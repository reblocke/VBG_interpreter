"""Synthetic capability matrix: numerical targets, provenance, and negative boundaries."""

from dataclasses import replace

import pytest

from vbg_interpreter import interpret_vbg
from vbg_interpreter.models import (
    BaseExcessBasis,
    CurrentChemistry,
    CurrentVbg,
    DrawSite,
    ExplorerContext,
    Hco3Basis,
    Pco2Unit,
    SaturationInput,
    SaturationUnit,
    SpecimenType,
    TriState,
    VbgExplorerRequest,
)
from vbg_interpreter.models import (
    CalculationStatus as Status,
)
from vbg_interpreter.models import (
    ChemistryTimeRelationship as Time,
)
from vbg_interpreter.serialization import to_json
from vbg_interpreter.venous_gas import sbe_from_ph_hco3


def request(**gas):
    if gas.get("pco2") is not None:
        gas.setdefault("pco2_unit", Pco2Unit.MMHG)
    return VbgExplorerRequest(CurrentVbg(**gas))


def eligible(**changes):
    gas = CurrentVbg(
        pco2=55,
        pco2_unit=Pco2Unit.MMHG,
        venous_o2_saturation=SaturationInput(75, SaturationUnit.PERCENTAGE_POINTS),
        saturation_same_sample=TriState.YES,
        specimen_type=SpecimenType.PERIPHERAL_VENOUS,
        draw_site=DrawSite.UPPER_EXTREMITY_PERIPHERAL,
    )
    return VbgExplorerRequest(
        replace(gas, **changes),
        context=ExplorerContext(TriState.NO, TriState.NO, TriState.NO, TriState.NO),
    )


def full_chemistry(**changes):
    return replace(CurrentChemistry(140, 105, 24, 40, 2, Time.SAME_CLINICAL_TIMEPOINT), **changes)


@pytest.mark.parametrize(
    "gas",
    [
        {"ph": 7.32},
        {"pco2": 55},
        {"hco3_mmol_l": 27},
        {"base_excess_mmol_l": -2},
        {"venous_o2_saturation": SaturationInput(75, SaturationUnit.PERCENTAGE_POINTS)},
    ],
)
def test_every_single_value_is_a_partial_result(gas):
    result = interpret_vbg(request(**gas))
    assert len(result.venous_gas.measured_values) == 1
    assert all(
        c.status is Status.UNAVAILABLE_MISSING_INPUT
        for c in result.venous_gas.calculated_values.values()
    )
    assert result.arterial_paco2_estimate.status is Status.UNAVAILABLE_MISSING_INPUT
    assert result.screening["status"] == "NOT_CONFIGURED"
    assert len(result.highest_value_next_inputs) <= 3


@pytest.mark.parametrize(
    "gas,axis,target",
    [
        ({"ph": 7.32, "pco2": 55}, "hco3", 28.34660584599947),
        ({"ph": 7.32, "hco3_mmol_l": 28.34660584599947}, "pco2", 55),
        ({"pco2": 55, "hco3_mmol_l": 28.34660584599947}, "ph", 7.32),
    ],
)
def test_hh_and_sbe_for_each_pair(gas, axis, target):
    result = interpret_vbg(request(**gas))
    coordinate = result.venous_gas.calculated_values[axis]
    assert coordinate.status is Status.AVAILABLE
    assert coordinate.values[axis] == pytest.approx(target, abs=1e-10)
    assert coordinate.output_provenance == "CALCULATED_HENDERSON_HASSELBALCH"
    assert result.venous_gas.standard_base_excess.values["sbe"] == pytest.approx(2.563403169179708)
    assert "37°C" in " ".join(result.venous_gas.standard_base_excess.limitations)
    assert result.arterial_paco2_estimate.status is not Status.AVAILABLE


def test_all_three_preserve_report_and_use_ph_pco2_for_sbe():
    result = interpret_vbg(request(ph=7.32, pco2=55, hco3_mmol_l=30, hco3_basis=Hco3Basis.UNKNOWN))
    gas = result.venous_gas
    assert gas.measured_values["hco3"]["value"] == 30
    assert gas.calculated_values == {}
    assert gas.consistency.values["reported_minus_hh"] == pytest.approx(1.65339415400053)
    assert gas.standard_base_excess.values["sbe"] == pytest.approx(2.563403169179708)
    assert not any("discord" in x.lower() for x in gas.consistency.limitations)


@pytest.mark.parametrize(
    "basis", [BaseExcessBasis.STANDARD, BaseExcessBasis.ACTUAL, BaseExcessBasis.UNKNOWN]
)
def test_reported_sbe_precedence_and_be_basis(basis):
    gas = interpret_vbg(
        request(ph=7.32, pco2=55, base_excess_mmol_l=-8, base_excess_basis=basis)
    ).venous_gas
    assert gas.measured_values["base_excess"]["value"] == -8
    sbe = gas.standard_base_excess
    assert sbe.values["sbe"] == pytest.approx(
        -8 if basis is BaseExcessBasis.STANDARD else 2.563403169179708
    )
    assert sbe.output_provenance == (
        "MEASURED_OR_REPORTED" if basis is BaseExcessBasis.STANDARD else "CALCULATED_VAN_SLYKE"
    )


def test_sbe_reference_equation_without_extra_thresholds():
    assert sbe_from_ph_hco3(ph=7.4, hco3_mmol_l=24.4) == 0
    assert sbe_from_ph_hco3(ph=7.2, hco3_mmol_l=12) == pytest.approx(-14.2704042)


@pytest.mark.parametrize(
    "oxygen,interval",
    [
        (TriState.NO, (45.72, 56.87)),
        (TriState.YES, (41.84, 59.78)),
        (TriState.UNKNOWN, (41.84, 59.78)),
    ],
)
def test_paco2_numeric_profiles_and_sign(oxygen, interval):
    req = eligible()
    req = replace(req, context=replace(req.context, supplemental_oxygen=oxygen))
    estimate = interpret_vbg(req).arterial_paco2_estimate
    assert estimate.status is Status.AVAILABLE
    assert estimate.applicability == "ELIGIBLE"
    assert estimate.values["point"] == pytest.approx(51.04)
    assert (estimate.values["lower"], estimate.values["upper"]) == pytest.approx(interval)
    assert estimate.evidence_tier == "EXTERNALLY_EVALUATED"


def test_explicit_units_are_equivalent_without_guessing():
    req = eligible(
        pco2=55 / 7.500616827041697,
        pco2_unit=Pco2Unit.KPA,
        venous_o2_saturation=SaturationInput(0.75, SaturationUnit.FRACTION_0_TO_1),
    )
    assert interpret_vbg(req).arterial_paco2_estimate.values["point"] == pytest.approx(51.04)
    low = interpret_vbg(
        eligible(venous_o2_saturation=SaturationInput(0.75, SaturationUnit.PERCENTAGE_POINTS))
    )
    assert low.arterial_paco2_estimate.values["point"] != pytest.approx(51.04)


@pytest.mark.parametrize(
    "same,status",
    [
        (TriState.YES, Status.AVAILABLE),
        (TriState.NO, Status.UNAVAILABLE_OUTSIDE_SCOPE),
        (TriState.UNKNOWN, Status.UNAVAILABLE_MISSING_INPUT),
    ],
)
def test_same_sample_is_a_real_gate(same, status):
    assert (
        interpret_vbg(eligible(saturation_same_sample=same)).arterial_paco2_estimate.status
        is status
    )


@pytest.mark.parametrize("specimen", list(SpecimenType))
def test_every_specimen(specimen):
    estimate = interpret_vbg(eligible(specimen_type=specimen)).arterial_paco2_estimate
    if specimen is SpecimenType.UNKNOWN:
        assert estimate.status is Status.AVAILABLE
        assert estimate.applicability == "APPLICABILITY_UNCERTAIN"
    elif specimen is SpecimenType.PERIPHERAL_VENOUS:
        assert estimate.applicability == "ELIGIBLE"
    else:
        assert estimate.status is Status.UNAVAILABLE_OUTSIDE_SCOPE


@pytest.mark.parametrize("site", list(DrawSite))
def test_every_draw_site(site):
    estimate = interpret_vbg(eligible(draw_site=site)).arterial_paco2_estimate
    if site is DrawSite.UNKNOWN:
        assert estimate.applicability == "APPLICABILITY_UNCERTAIN"
    elif site is DrawSite.UPPER_EXTREMITY_PERIPHERAL:
        assert estimate.applicability == "ELIGIBLE"
    else:
        assert estimate.status is Status.UNAVAILABLE_OUTSIDE_SCOPE


@pytest.mark.parametrize(
    "field",
    [
        "known_poor_perfusion_or_hemodynamic_instability",
        "recent_major_ventilation_or_treatment_change",
        "material_preanalytic_concern",
    ],
)
@pytest.mark.parametrize("value", [TriState.YES, TriState.UNKNOWN])
def test_context_unknown_is_not_favorable_and_known_risks_block(field, value):
    req = eligible()
    estimate = interpret_vbg(
        replace(req, context=replace(req.context, **{field: value}))
    ).arterial_paco2_estimate
    assert (
        (estimate.status is Status.UNAVAILABLE_OUTSIDE_SCOPE)
        if value is TriState.YES
        else (estimate.applicability == "APPLICABILITY_UNCERTAIN")
    )


def test_derived_pco2_never_enters_arterial_model():
    req = eligible(ph=7.32, pco2=None, pco2_unit=None, hco3_mmol_l=27)
    result = interpret_vbg(req)
    assert result.venous_gas.calculated_values["pco2"].status is Status.AVAILABLE
    assert result.arterial_paco2_estimate.status is Status.UNAVAILABLE_MISSING_INPUT
    assert result.arterial_paco2_estimate.values == {}


@pytest.mark.parametrize(
    "chem,expected",
    [
        (CurrentChemistry(), {}),
        (CurrentChemistry(140, 105), {"sodium_chloride_difference": 35}),
        (CurrentChemistry(140, 105, 24), {"anion_gap": 11, "sodium_chloride_difference": 35}),
        (
            CurrentChemistry(140, 105, 24, 20),
            {"anion_gap": 11, "corrected_anion_gap": 16, "sodium_chloride_difference": 35},
        ),
    ],
)
def test_progressive_chemistry(chem, expected):
    result = interpret_vbg(replace(request(ph=7.32), current_chemistry=chem))
    for key, calc in result.chemistry.items():
        if key in expected:
            assert list(calc.values.values()) == pytest.approx([expected[key]])
        else:
            assert calc.status is not Status.AVAILABLE


@pytest.mark.parametrize("reported", [True, False])
@pytest.mark.parametrize("lactate", [None, 2.0])
def test_upstream_partition_closes_with_reported_or_calculated_sbe(reported, lactate):
    req = request(
        ph=7.32,
        pco2=55,
        **(
            {"base_excess_mmol_l": -2, "base_excess_basis": BaseExcessBasis.STANDARD}
            if reported
            else {}
        ),
    )
    result = interpret_vbg(replace(req, current_chemistry=full_chemistry(lactate_mmol_l=lactate)))
    part = result.chemistry["venous_stewart_partition"]
    assert part.status is Status.AVAILABLE
    assert part.values["closure_error"] == pytest.approx(0, abs=1e-10)
    assert part.values["total_sbe"] == pytest.approx(-2 if reported else 2.563403169179708)
    assert part.input_origins["sbe"] == (
        "MEASURED_OR_REPORTED" if reported else "CALCULATED_VAN_SLYKE"
    )
    assert ("lactate_component" in part.values) == (lactate is not None)


def test_missing_sbe_and_derived_ph_do_not_enable_partition():
    for req in (request(ph=7.32), request(pco2=55, hco3_mmol_l=27)):
        result = interpret_vbg(replace(req, current_chemistry=full_chemistry()))
        assert (
            result.chemistry["venous_stewart_partition"].status is Status.UNAVAILABLE_MISSING_INPUT
        )


@pytest.mark.parametrize("relation", [Time.UNKNOWN, Time.DIFFERENT_TIMEPOINT])
def test_partition_requires_same_timepoint(relation):
    result = interpret_vbg(
        replace(
            request(ph=7.32, pco2=55),
            current_chemistry=full_chemistry(relationship_to_vbg=relation),
        )
    )
    part = result.chemistry["venous_stewart_partition"]
    assert part.status is (
        Status.UNAVAILABLE_MISSING_INPUT
        if relation is Time.UNKNOWN
        else Status.UNAVAILABLE_OUTSIDE_SCOPE
    )


def test_numerical_failure_keeps_independent_outputs():
    result = interpret_vbg(replace(eligible(ph=400), current_chemistry=full_chemistry()))
    assert result.venous_gas.calculated_values["hco3"].status is Status.MODEL_DOMAIN_REFUSAL
    assert result.venous_gas.standard_base_excess.status is Status.MODEL_DOMAIN_REFUSAL
    assert result.arterial_paco2_estimate.status is Status.AVAILABLE
    assert result.chemistry["anion_gap"].status is Status.AVAILABLE
    assert result.venous_gas.measured_values["ph"]["value"] == 400


def test_chemistry_arithmetic_failure_does_not_destroy_gas():
    result = interpret_vbg(
        replace(request(ph=7.32), current_chemistry=CurrentChemistry(1, 1e308, 1e308))
    )
    assert result.chemistry["anion_gap"].status is Status.MODEL_DOMAIN_REFUSAL
    assert result.venous_gas.measured_values["ph"]["value"] == 7.32


def test_nonpositive_interval_is_refused_without_clamping():
    result = interpret_vbg(eligible(pco2=5))
    assert result.arterial_paco2_estimate.status is Status.MODEL_DOMAIN_REFUSAL
    assert result.arterial_paco2_estimate.values == {}


def test_priority_order_and_no_chemistry_imputation():
    result = interpret_vbg(request(pco2=55))
    assert "saturation" in result.highest_value_next_inputs[0]
    assert "venous pH" in result.highest_value_next_inputs[1]
    assert "anion gap" in result.highest_value_next_inputs[2]
    assert not any("requires" in line for line in result.unresolved_questions)
    result = interpret_vbg(
        replace(
            eligible(draw_site=DrawSite.FEMORAL), current_chemistry=CurrentChemistry(140, 105, 24)
        )
    )
    assert not any("saturation" in line for line in result.highest_value_next_inputs)
    assert any("Albumin" in line for line in result.highest_value_next_inputs)


def test_serialization_and_exact_allowed_result_surface():
    req = replace(eligible(ph=7.32), current_chemistry=full_chemistry())
    result = interpret_vbg(req)
    assert to_json(result) == to_json(interpret_vbg(req))
    assert set(result.to_dict()) == {
        "schema_version",
        "software_version",
        "input_summary",
        "venous_gas",
        "chemistry",
        "screening",
        "arterial_paco2_estimate",
        "unresolved_questions",
        "highest_value_next_inputs",
        "methods",
    }
    assert set(result.arterial_paco2_estimate.values) == {
        "measured_pvco2",
        "saturation_percent",
        "point",
        "lower",
        "upper",
        "oxygen_profile",
    }
    assert set(result.input_summary) == {
        "schema_version",
        "current_vbg",
        "current_chemistry",
        "context",
    }
    assert len(result.highest_value_next_inputs) <= 3


def test_serum_total_co2_never_completes_gas_or_sbe():
    result = interpret_vbg(replace(request(ph=7.32), current_chemistry=full_chemistry()))
    assert result.venous_gas.calculated_values["pco2"].status is Status.UNAVAILABLE_MISSING_INPUT
    assert result.venous_gas.standard_base_excess.status is Status.UNAVAILABLE_MISSING_INPUT


def test_partition_reports_sbe_numerical_failure_not_missing_measurement():
    result = interpret_vbg(replace(request(ph=400, pco2=55), current_chemistry=full_chemistry()))
    assert result.chemistry["venous_stewart_partition"].status is Status.MODEL_DOMAIN_REFUSAL
    assert not any("Adding reported or calculable" in x for x in result.highest_value_next_inputs)


@pytest.mark.parametrize(
    "ph,position", [(7.349, "below"), (7.35, "within"), (7.45, "within"), (7.451, "above")]
)
def test_descriptive_reference_band_boundaries(ph, position):
    assert interpret_vbg(request(ph=ph)).venous_gas.ph_reference_position == position


def test_hco3_provenance_is_retained_in_derived_sbe():
    result = interpret_vbg(request(ph=7.32, hco3_mmol_l=27, hco3_basis=Hco3Basis.UNKNOWN))
    assert result.venous_gas.standard_base_excess.input_origins["hco3_basis"] == "UNKNOWN"


def test_applicability_does_not_override_known_blocker_and_invalid_unit_domain():
    result = interpret_vbg(eligible(specimen_type=SpecimenType.UNKNOWN, draw_site=DrawSite.FEMORAL))
    assert result.arterial_paco2_estimate.status is Status.UNAVAILABLE_OUTSIDE_SCOPE
    result = interpret_vbg(
        replace(eligible(pco2=1e308, pco2_unit=Pco2Unit.KPA), current_chemistry=full_chemistry())
    )
    assert result.arterial_paco2_estimate.status is Status.MODEL_DOMAIN_REFUSAL
    assert result.chemistry["anion_gap"].status is Status.AVAILABLE
