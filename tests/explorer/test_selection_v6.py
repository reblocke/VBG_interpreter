"""Independent synthetic selection oracles for the v0.6 capability contract."""

# The oracle intentionally uses explicit constants and dependencies, never the production selector.
import itertools
import json
import math
from copy import deepcopy
from dataclasses import replace

import pytest
from test_foundation import wire_request

from vbg_interpreter import interpret_vbg
from vbg_interpreter.mapping import request_from_mapping
from vbg_interpreter.models import (
    AlbuminInput,
    AlbuminUnit,
    BaseExcessBasis,
    ChemistryTimeRelationship,
    CurrentChemistry,
    CurrentVbg,
    ExplorerInputError,
    Hco3Basis,
    Pco2Unit,
    SampleType,
    SaturationInput,
    SaturationUnit,
    VbgExplorerRequest,
)
from vbg_interpreter.serialization import to_json


def result(**fields):
    if fields.get("pco2") is not None:
        fields.setdefault("pco2_unit", Pco2Unit.MMHG)
    return interpret_vbg(VbgExplorerRequest(CurrentVbg(**fields)))


def test_untouched_unknown_uses_saturation():
    r = result(
        ph=7.32, pco2=55, venous_o2_saturation=SaturationInput(75, SaturationUnit.PERCENTAGE_POINTS)
    )
    assert r.arterial_paco2_estimate.values["point"] == pytest.approx(51.04)


def test_hh_pair_supports_chained_estimate():
    r = result(ph=7.32, hco3_mmol_l=28.34660584599947)
    assert r.arterial_paco2_estimate.values["point"] == pytest.approx(50)


def test_positive_point_survives_nonphysical_interval():
    r = result(pco2=10, venous_o2_saturation=SaturationInput(75, SaturationUnit.PERCENTAGE_POINTS))
    assert r.arterial_paco2_estimate.values["point"] == pytest.approx(6.04)


P, C, H = 7.32, 55, 28.34660584599947
ABS, REL = 1e-10, 1e-12
BITS = list(itertools.product((False, True), repeat=5))
CORE = list(itertools.product((False, True), repeat=3))
SAME = ChemistryTimeRelationship.SAME_CLINICAL_TIMEPOINT


def close(actual, expected):
    assert actual == pytest.approx(expected, abs=ABS, rel=REL)


def make_gas(bits, sample=SampleType.UNKNOWN, **kwargs):
    p, c, h, be, sat = bits
    fields = dict(
        ph=P if p else None,
        pco2=C if c else None,
        pco2_unit=Pco2Unit.MMHG if c else None,
        hco3_mmol_l=H if h else None,
        base_excess_mmol_l=0 if be else None,
        base_excess_basis=BaseExcessBasis.STANDARD if be else BaseExcessBasis.UNKNOWN,
        venous_o2_saturation=SaturationInput(75, SaturationUnit.PERCENTAGE_POINTS) if sat else None,
        sample_type=sample,
    )
    fields.update(kwargs)
    return CurrentVbg(**fields)


def make_chem(bits=(True,) * 5, timing=SAME, albumin_unit=AlbuminUnit.G_L):
    na, cl, bmp, alb, lac = bits
    return CurrentChemistry(
        sodium_mmol_l=140 if na else None,
        chloride_mmol_l=104 if cl else None,
        serum_total_co2_mmol_l=24 if bmp else None,
        albumin=AlbuminInput(40 if albumin_unit is AlbuminUnit.G_L else 4, albumin_unit)
        if alb
        else None,
        lactate_mmol_l=0 if lac else None,
        relationship_to_vbg=timing,
    )


def assert_oracle(req, r):
    g, chem = req.current_vbg, req.current_chemistry
    p = g.ph
    c = (
        None
        if g.pco2 is None
        else g.pco2 * (7.500616827041697 if g.pco2_unit is Pco2Unit.KPA else 1)
    )
    h = g.hco3_mmol_l
    if p is None and c is not None and h is not None:
        p = 6.095 + math.log10(h / (0.0307 * c))
    if c is None and p is not None and h is not None:
        c = h / (0.0307 * 10 ** (p - 6.095))
    farkas = g.venous_o2_saturation is not None and g.sample_type is not SampleType.CENTRAL
    expected_method = "farkas_simplified_93_v1" if farkas else "fixed_paco2_offset_v1"
    co2, ph = r.arterial_paco2_estimate, r.arterial_ph_estimate
    assert co2.method_id == expected_method
    assert ph.method_id == "fixed_ph_offset_v1"
    for axis, raw, resolved, calc in (("ph", g.ph, p, ph), ("pco2", g.pco2, c, co2)):
        assert (calc.status == "AVAILABLE") == (resolved is not None)
        origin = (
            "SUPPLIED"
            if raw is not None
            else "HH_RECONSTRUCTED"
            if resolved is not None
            else "UNAVAILABLE"
        )
        assert calc.selection.source_coordinate_origin == origin
        if raw is not None:
            source_entry = calc.selection.source_values[axis]
            close(source_entry["value"], raw)
            assert source_entry["units"] == (g.pco2_unit if axis == "pco2" else "pH units")
        assert calc.selection.sample_type_as_entered == g.sample_type
        assert calc.selection.interpretation_suitable == (resolved is not None)
        if resolved is not None:
            close(calc.selection.source_value, resolved)
            assert calc.selection.derivation_method_id == (
                "henderson_hasselbalch_v1" if origin == "HH_RECONSTRUCTED" else None
            )
        assert (r.physiology_direction["axes"][axis]["bound"] is not None) == (raw is not None)
    expected_scope = (
        "CENTRAL_HEURISTIC"
        if g.sample_type is SampleType.CENTRAL
        else "PERIPHERAL_ASSUMPTION"
        if farkas and g.sample_type is SampleType.UNKNOWN
        else "PERIPHERAL_CATEGORY_MATCH"
        if farkas
        else "UNASSESSED"
    )
    assert co2.selection.model_scope == expected_scope
    if p is not None:
        close(ph.values["ph"], p + 0.04)
    point = None
    if c is not None:
        sat = g.venous_o2_saturation
        percent = (
            None
            if sat is None
            else sat.value * (100 if sat.unit is SaturationUnit.FRACTION_0_TO_1 else 1)
        )
        point = c - (0.22 * (93 - percent) if farkas else 5)
        close(co2.values["point"], point)
        if farkas:
            reason = (
                "FARKAS_SUPPLIED_PVCO2_AND_SATURATION"
                if g.pco2 is not None
                else "FARKAS_RECONSTRUCTED_PVCO2_CHAIN"
            )
            assert reason in co2.selection.reason_codes
            if g.sample_type is SampleType.UNKNOWN:
                assert "FARKAS_UNKNOWN_SAMPLE_PERIPHERAL_ASSUMPTION" in co2.selection.reason_codes
    interval = farkas and g.pco2 is not None
    assert (co2.agreement.status == "AVAILABLE") == interval
    if interval:
        close(co2.agreement.lower, point - 9.20)
        close(co2.agreement.upper, point + 8.74)
    else:
        assert co2.agreement.lower is co2.agreement.upper is None
    pair = p is not None and c is not None
    assert (r.modeled_arterial_hco3.status == "AVAILABLE") == pair
    assert (r.provisional_interpretation.status == "AVAILABLE") == pair
    if pair:
        close(
            r.modeled_arterial_hco3.values["modeled_hco3"],
            0.0307 * point * 10 ** (p + 0.04 - 6.095),
        )
    if pair and not interval:
        assert r.interpretation_sensitivity["status"] == "NOT_QUANTIFIED"
    sbe = r.venous_gas.standard_base_excess
    reported = g.base_excess_mmol_l is not None and g.base_excess_basis is BaseExcessBasis.STANDARD
    assert (sbe.status == "AVAILABLE") == (reported or pair)
    assert sbe.method_id == (
        "reported_venous_sbe_v1" if reported else "venous_sbe_van_slyke_37c_v1"
    )
    if reported:
        close(sbe.values["sbe"], g.base_excess_mmol_l)
    elif pair:
        hh = 0.0307 * c * 10 ** (p - 6.095) if g.ph is not None and g.pco2 is not None else h
        close(sbe.values["sbe"], 0.9287 * (hh - 24.4 + 14.83 * (p - 7.4)))
    na, cl, bmp, alb = (
        chem.sodium_mmol_l,
        chem.chloride_mmol_l,
        chem.serum_total_co2_mmol_l,
        chem.albumin,
    )
    ag = all(v is not None for v in (na, cl, bmp))
    assert (r.chemistry["anion_gap"].status == "AVAILABLE") == ag
    assert (r.chemistry["corrected_anion_gap"].status == "AVAILABLE") == (ag and alb is not None)
    assert (r.chemistry["sodium_chloride_difference"].status == "AVAILABLE") == (
        na is not None and cl is not None
    )
    if ag:
        close(r.chemistry["anion_gap"].values["anion_gap"], na - cl - bmp)
    if ag and alb is not None:
        normalized_alb = alb.value * (10 if alb.unit is AlbuminUnit.G_DL else 1)
        close(
            r.chemistry["corrected_anion_gap"].values["corrected_anion_gap"],
            na - cl - bmp + 0.25 * (40 - normalized_alb),
        )
    stewart = (
        g.ph is not None
        and (reported or pair)
        and all(v is not None for v in (na, cl, alb))
        and chem.relationship_to_vbg is SAME
    )
    assert (r.chemistry["venous_stewart_partition"].status == "AVAILABLE") == stewart
    comparison = r.chemistry["bmp_gas_bicarbonate_comparison"]
    direct_pair = g.ph is not None and g.pco2 is not None
    assert (comparison.status == "AVAILABLE") == (
        bmp is not None and (direct_pair or h is not None)
    )
    if comparison.status == "AVAILABLE":
        basis = 0.0307 * c * 10 ** (p - 6.095) if direct_pair else h
        close(comparison.values["bmp_minus_gas_hco3"], bmp - basis)
        assert comparison.values["gas_basis"] == (
            "HH_FROM_MEASURED_PH_PVCO2" if direct_pair else "SUPPLIED_BLOOD_GAS_HCO3"
        )


@pytest.mark.parametrize(
    "gas_bits,chem_bits,sample", list(itertools.product(BITS, BITS, list(SampleType)))
)
def test_complete_availability_matrix(gas_bits, chem_bits, sample):
    # Build all 3,072 strict browser-shaped payloads, including invalid empty-gas cases.
    payload = wire_request(
        VbgExplorerRequest(
            make_gas(gas_bits if any(gas_bits) else (True, False, False, False, False), sample),
            make_chem(chem_bits),
        )
    )
    if not any(gas_bits):
        payload["current_vbg"]["ph"] = None
        with pytest.raises(ExplorerInputError, match="at least one"):
            request_from_mapping(payload)
        return
    before = deepcopy(payload)
    req = request_from_mapping(payload)
    original = req.to_dict()
    r = interpret_vbg(req)
    assert_oracle(req, r)
    assert payload == before and req.to_dict() == original
    serialized = to_json(r)
    assert serialized == to_json(interpret_vbg(req))
    assert "NaN" not in serialized and "Infinity" not in serialized
    assert json.loads(serialized)["schema_version"] == "vbg_explorer_result/6.1"


GAS_PROVENANCE = [
    (bits, basis)
    for bits in CORE
    for basis in (list(Hco3Basis) if bits[2] else [Hco3Basis.UNKNOWN])
]
BE_STATES = [None, *BaseExcessBasis]


@pytest.mark.parametrize(
    "core,hbasis,be,timing,lactate",
    [
        (bits, hb, be, time, lac)
        for (bits, hb), be, time, lac in itertools.product(
            GAS_PROVENANCE, BE_STATES, list(ChemistryTimeRelationship), (False, True)
        )
    ],
)
def test_provenance_be_timing_product(core, hbasis, be, timing, lactate):
    gas = make_gas(
        (*core, be is not None, True),
        hco3_basis=hbasis,
        base_excess_basis=be or BaseExcessBasis.UNKNOWN,
    )
    req = VbgExplorerRequest(gas, make_chem((True, True, True, True, lactate), timing))
    r = interpret_vbg(req)
    assert_oracle(req, r)
    for component in (r.arterial_ph_estimate, r.arterial_paco2_estimate):
        if component.selection.source_coordinate_origin == "HH_RECONSTRUCTED":
            assert component.selection.source_values["hco3"]["basis"] == hbasis


PRESSURES = [(bits, unit) for bits in CORE for unit in (list(Pco2Unit) if bits[1] else [None])]


@pytest.mark.parametrize(
    "core,unit,sat_unit,sample",
    [
        (bits, unit, sat, sample)
        for (bits, unit), sat, sample in itertools.product(
            PRESSURES, [None, *SaturationUnit], list(SampleType)
        )
    ],
)
def test_pressure_saturation_product(core, unit, sat_unit, sample):
    sat = (
        None
        if sat_unit is None
        else SaturationInput(0.75 if sat_unit is SaturationUnit.FRACTION_0_TO_1 else 75, sat_unit)
    )
    gas = make_gas(
        (*core, True, False),
        sample,
        pco2=(C / 7.500616827041697 if unit is Pco2Unit.KPA else C) if core[1] else None,
        pco2_unit=unit,
        venous_o2_saturation=sat,
    )
    req = request_from_mapping(wire_request(VbgExplorerRequest(gas)))
    assert_oracle(req, interpret_vbg(req))


ALBUMINS = [
    (bits, unit) for bits in BITS for unit in (list(AlbuminUnit) if bits[3] else [AlbuminUnit.G_L])
]


@pytest.mark.parametrize(
    "bits,unit,timing,derived_ph",
    [
        (bits, unit, time, derived)
        for (bits, unit), time, derived in itertools.product(
            ALBUMINS, list(ChemistryTimeRelationship), (False, True)
        )
    ],
)
def test_albumin_chemistry_product(bits, unit, timing, derived_ph):
    gas = make_gas((not derived_ph, True, derived_ph, True, False))
    req = request_from_mapping(wire_request(VbgExplorerRequest(gas, make_chem(bits, timing, unit))))
    assert_oracle(req, interpret_vbg(req))


@pytest.mark.parametrize("sat,point", [(0, 34.54), (93, 55), (100, 56.54), (93 - 5 / 0.22, 50)])
def test_saturation_edges_keep_selected_method(sat, point):
    r = result(pco2=55, venous_o2_saturation=SaturationInput(sat, SaturationUnit.PERCENTAGE_POINTS))
    close(r.arterial_paco2_estimate.values["point"], point)
    assert r.arterial_paco2_estimate.method_id == "farkas_simplified_93_v1"


def test_chained_warning_and_supplied_axis_precedence():
    for fields in ({"ph": 7.32, "hco3_mmol_l": 120}, {"pco2": 55, "hco3_mmol_l": 120}):
        r = result(**fields)
        assert r.input_observations
        assert r.provisional_interpretation.status == "UNAVAILABLE_UNRELIABLE_INPUT"
        assert r.arterial_ph_estimate.selection.interpretation_suitable == ("ph" in fields)
        assert r.arterial_paco2_estimate.selection.interpretation_suitable == ("pco2" in fields)
    r = result(
        ph=0.32,
        pco2=55,
        hco3_mmol_l=H,
        venous_o2_saturation=SaturationInput(75, SaturationUnit.PERCENTAGE_POINTS),
    )
    assert r.arterial_ph_estimate.selection.source_coordinate_origin == "SUPPLIED"
    assert not r.arterial_ph_estimate.selection.interpretation_suitable
    assert r.arterial_paco2_estimate.selection.interpretation_suitable
    assert r.provisional_interpretation.status == "UNAVAILABLE_UNRELIABLE_INPUT"
    # A flagged operand suppresses the dependent chain, not finite arithmetic.
    r = result(ph=0.32, hco3_mmol_l=H)
    assert r.arterial_paco2_estimate.status == "AVAILABLE"
    assert not r.arterial_paco2_estimate.selection.interpretation_suitable


@pytest.mark.parametrize("ph", [None, 0.32])
def test_direct_bicarbonates_ignore_unrelated_flagged_ph(ph):
    req = VbgExplorerRequest(
        CurrentVbg(ph=ph, hco3_mmol_l=25), CurrentChemistry(serum_total_co2_mmol_l=12)
    )
    c = interpret_vbg(req).chemistry["bmp_gas_bicarbonate_comparison"]
    close(c.values["bmp_minus_gas_hco3"], -13)


def test_negative_farkas_point_preserves_selected_failure():
    r = result(pco2=3, venous_o2_saturation=SaturationInput(75, SaturationUnit.PERCENTAGE_POINTS))
    c = r.arterial_paco2_estimate
    assert c.status == "MODEL_DOMAIN_REFUSAL"
    assert c.method_id == "farkas_simplified_93_v1" and c.values == {}
    assert "SELECTED_METHOD_NUMERICAL_FAILURE" in c.selection.reason_codes


def test_equivalent_reconstruction_changes_evidence_not_point():
    full = make_gas((True, True, False, False, True))
    baseline = interpret_vbg(VbgExplorerRequest(full))
    for gas in (
        replace(full, pco2=None, pco2_unit=None, hco3_mmol_l=H),
        replace(full, ph=None, hco3_mmol_l=H),
    ):
        r = interpret_vbg(VbgExplorerRequest(gas))
        close(r.arterial_ph_estimate.values["ph"], baseline.arterial_ph_estimate.values["ph"])
        close(
            r.arterial_paco2_estimate.values["point"],
            baseline.arterial_paco2_estimate.values["point"],
        )
        assert (r.arterial_paco2_estimate.agreement.status == "AVAILABLE") == (gas.pco2 is not None)
        assert "unvalidated" in " ".join(r.provisional_interpretation.limitations)
    redundant = interpret_vbg(VbgExplorerRequest(replace(full, hco3_mmol_l=40)))
    assert redundant.arterial_ph_estimate == baseline.arterial_ph_estimate
    assert redundant.arterial_paco2_estimate == baseline.arterial_paco2_estimate
    assert redundant.venous_gas.consistency.values["reported_minus_hh"] != 0


@pytest.mark.parametrize("ph,h,bmp", [(None, 120, 12), (0.32, 25, 120)])
def test_bicarbonate_warnings_preserve_direct_finite_subtraction(ph, h, bmp):
    r = interpret_vbg(
        VbgExplorerRequest(
            CurrentVbg(ph=ph, hco3_mmol_l=h), CurrentChemistry(serum_total_co2_mmol_l=bmp)
        )
    )
    assert r.input_observations
    close(r.chemistry["bmp_gas_bicarbonate_comparison"].values["bmp_minus_gas_hco3"], bmp - h)
