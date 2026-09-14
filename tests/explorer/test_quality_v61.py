"""Dependency-specific sanity warnings through the real strict/browser contract."""

import json
import math
from copy import deepcopy

import pytest
from test_foundation import wire_request

from vbg_interpreter import interpret_vbg
from vbg_interpreter.mapping import request_from_mapping
from vbg_interpreter.models import CurrentVbg, Pco2Unit, VbgExplorerRequest
from vbg_interpreter.serialization import to_json


def run(**fields):
    if "pco2" in fields:
        fields.setdefault("pco2_unit", Pco2Unit.MMHG)
    payload = wire_request(VbgExplorerRequest(CurrentVbg(**fields)))
    original = deepcopy(payload)
    request = request_from_mapping(payload)
    result = interpret_vbg(request)
    serialized = to_json(result)
    assert serialized == to_json(interpret_vbg(request))
    assert payload == original
    json.loads(serialized, parse_constant=lambda s: pytest.fail(s))
    return result


@pytest.mark.parametrize(
    "fields,axis,expected,warning_field,origin",
    [
        (
            {"ph": 7.32, "hco3_mmol_l": 270},
            "pco2",
            270 / (0.0307 * 10**1.225),
            "pco2",
            "HH_RECONSTRUCTED",
        ),
        (
            {"ph": 7, "hco3_mmol_l": 95},
            "pco2",
            95 / (0.0307 * 10**0.905),
            "pco2",
            "HH_RECONSTRUCTED",
        ),
        ({"ph": 7.6, "hco3_mmol_l": 120}, "pco2", 120 / (0.0307 * 10**1.505), "hco3", "SUPPLIED"),
        (
            {"pco2": 55, "hco3_mmol_l": 120},
            "ph",
            6.095 + math.log10(120 / (0.0307 * 55)),
            "hco3",
            "SUPPLIED",
        ),
        (
            {"pco2": 10, "hco3_mmol_l": 100},
            "ph",
            6.095 + math.log10(100 / 0.307),
            "ph",
            "HH_RECONSTRUCTED",
        ),
    ],
)
def test_chained_warning_retains_finite_numbers_without_classification(
    fields, axis, expected, warning_field, origin
):
    r = run(**fields)
    component = r.arterial_ph_estimate if axis == "ph" else r.arterial_paco2_estimate
    assert component.status == "AVAILABLE"
    assert component.selection.source_value == pytest.approx(expected)
    assert not component.selection.interpretation_suitable
    assert any(
        o["field"] == warning_field and o["origin"] == origin for o in component.input_warnings
    )
    assert r.provisional_interpretation.status == "UNAVAILABLE_UNRELIABLE_INPUT"
    assert r.interpretation_sensitivity["status"] == "UNAVAILABLE_UNRELIABLE_INPUT"
    supplied_axis = "pco2" if axis == "ph" else "ph"
    assert r.physiology_direction["axes"][supplied_axis]["status"] == "AVAILABLE"
    assert r.physiology_direction["axes"][axis]["status"] == "UNAVAILABLE_MISSING_INPUT"
    assert r.venous_gas.standard_base_excess.status == "AVAILABLE"


def test_unused_reported_bicarbonate_warning_does_not_taint_supplied_pair():
    r = run(ph=7.32, pco2=55, hco3_mmol_l=270)
    assert r.provisional_interpretation.status == "AVAILABLE"
    for c in (r.arterial_ph_estimate, r.arterial_paco2_estimate, r.venous_gas.standard_base_excess):
        assert not c.input_warnings
    assert r.venous_gas.consistency.input_warnings


@pytest.mark.parametrize("axis,value", [("ph", 5.9), ("ph", 8.6), ("pco2", 4.9), ("pco2", 251)])
def test_supplied_and_reconstructed_extremes_share_sanity_policy(axis, value):
    from vbg_interpreter.models import SaturationInput, SaturationUnit

    sat = SaturationInput(100, SaturationUnit.PERCENTAGE_POINTS)
    if axis == "ph":
        direct = dict(ph=value, pco2=55)
        chained = dict(pco2=55, hco3_mmol_l=0.0307 * 55 * 10 ** (value - 6.095))
    else:
        direct = dict(ph=7.32, pco2=value)
        chained = dict(ph=7.32, hco3_mmol_l=0.0307 * value * 10 ** (7.32 - 6.095))
    a, b = [run(**fields, venous_o2_saturation=sat) for fields in (direct, chained)]
    for r in (a, b):
        c = r.arterial_ph_estimate if axis == "ph" else r.arterial_paco2_estimate
        assert c.status == "AVAILABLE"
        assert not c.selection.interpretation_suitable
        assert any(o["field"] == axis for o in c.input_warnings)
        assert r.provisional_interpretation.status == "UNAVAILABLE_UNRELIABLE_INPUT"
    if axis == "pco2":
        assert b.arterial_paco2_estimate.agreement.status == "NOT_QUANTIFIED"
    else:
        assert a.arterial_paco2_estimate.agreement == b.arterial_paco2_estimate.agreement


@pytest.mark.parametrize("axis,value", [("ph", 6), ("ph", 8.5), ("pco2", 5), ("pco2", 250)])
def test_inclusive_sanity_boundaries(axis, value):
    r = run(**{axis: value})
    assert not r.input_observations


@pytest.mark.parametrize("pressure_unit", list(Pco2Unit))
def test_unit_normalization_retains_same_warning_and_original_input(pressure_unit):
    value = 300 if pressure_unit is Pco2Unit.MMHG else 300 / 7.500616827041697
    r = run(pco2=value, pco2_unit=pressure_unit, hco3_mmol_l=25)
    assert any(o["field"] == "pco2" for o in r.arterial_ph_estimate.input_warnings)
    original = r.arterial_ph_estimate.selection.source_values["pco2"]
    assert original["value"] == value
    assert original["units"] == pressure_unit


def test_dependency_qualifications_on_independent_arithmetic_and_reported_sbe():
    from vbg_interpreter.models import BaseExcessBasis, CurrentChemistry

    request = VbgExplorerRequest(
        CurrentVbg(
            ph=7.32,
            hco3_mmol_l=270,
            base_excess_mmol_l=0,
            base_excess_basis=BaseExcessBasis.STANDARD,
        ),
        CurrentChemistry(sodium_mmol_l=300, chloride_mmol_l=100, serum_total_co2_mmol_l=12),
    )
    r = interpret_vbg(request_from_mapping(wire_request(request)))
    assert not r.venous_gas.standard_base_excess.input_warnings
    assert r.venous_gas.standard_base_excess.values["sbe"] == 0
    comparison = r.chemistry["bmp_gas_bicarbonate_comparison"]
    assert comparison.status == "AVAILABLE"
    assert {o["field"] for o in comparison.input_warnings} == {"hco3"}
    for key in ("anion_gap", "sodium_chloride_difference"):
        c = r.chemistry[key]
        assert c.status == "AVAILABLE"
        assert {o["field"] for o in c.input_warnings} == {"sodium"}


def test_reviewer_farkas_example_retains_exact_point_and_fails_local_interpretation():
    from vbg_interpreter.models import SaturationInput, SaturationUnit

    r = run(
        ph=7.32,
        hco3_mmol_l=270,
        venous_o2_saturation=SaturationInput(75, SaturationUnit.PERCENTAGE_POINTS),
    )
    c = r.arterial_paco2_estimate
    assert c.values["point"] == pytest.approx(519.9122434945687, abs=1e-10)
    assert c.method_id == "farkas_simplified_93_v1"
    assert c.agreement.status == "NOT_QUANTIFIED"
    assert r.arterial_ph_estimate.selection.interpretation_suitable
    assert not c.selection.interpretation_suitable
