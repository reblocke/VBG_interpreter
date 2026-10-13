"""Synthetic v0.5 acceptance gates, including failure propagation and source boundaries."""

from dataclasses import replace

import pytest
from stewartlight.interpret import assess_boston

from vbg_interpreter import interpret_vbg
from vbg_interpreter.best_guess import (
    _adapt_assessment,
    _EstimatedGas,
    interpretation_sensitivity,
)
from vbg_interpreter.models import (
    AlbuminInput,
    AlbuminUnit,
    CurrentChemistry,
    CurrentVbg,
    Pco2Unit,
    SampleType,
    SaturationInput,
    SaturationUnit,
    VbgExplorerRequest,
)
from vbg_interpreter.models import (
    CalculationStatus as Status,
)
from vbg_interpreter.models import (
    ChemistryTimeRelationship as Time,
)
from vbg_interpreter.serialization import to_json, to_primitive


def result(ph=7.32, pco2=55, sample=SampleType.PERIPHERAL, sat=None, chemistry=None, **extra):
    return interpret_vbg(
        VbgExplorerRequest(
            CurrentVbg(
                ph=ph,
                pco2=pco2,
                pco2_unit=Pco2Unit.MMHG if pco2 is not None else None,
                sample_type=sample,
                venous_o2_saturation=None
                if sat is None
                else SaturationInput(sat, SaturationUnit.PERCENTAGE_POINTS),
                **extra,
            ),
            chemistry or CurrentChemistry(),
        )
    )


def test_sensitivity_recomputes_hh_and_exposes_changed_compensation():
    r = result(7.21, 29, sat=75)
    scenarios = r.interpretation_sensitivity["scenarios"]
    # Browser checks displayed scenario values, not compensation categories or ranges.
    assert [s["assessment"]["compensation_category"] for s in scenarios] == [
        "BELOW",
        "WITHIN",
        "ABOVE",
    ]
    assert [
        s["assessment"]["expected_compensation"]["lower_mmhg"] for s in scenarios
    ] == pytest.approx([16.422809779, 22.476461924, 28.227431461], abs=1e-6)


def test_unchanged_scenarios_are_not_called_full_robustness():
    r = result(7.10, 100, sat=75)
    assert r.interpretation_sensitivity["status"] == "NO_CHANGE_TESTED"
    assert r.interpretation_sensitivity["summary"] == (
        "No change in the tested CO₂ scenarios; pH uncertainty and full "
        "robustness remain unassessed."
    )


def test_failed_sensitivity_scenario_never_claims_robustness(monkeypatch):
    import vbg_interpreter.best_guess as module

    r = result(sat=75)
    original = module.assess_estimated_gas

    def refuse_lower(ph, co2, hco3):
        assessment = original(ph, co2, hco3)
        return (
            replace(assessment, status=Status.MODEL_DOMAIN_REFUSAL)
            if co2.values["point"] == co2.agreement.lower
            else assessment
        )

    monkeypatch.setattr(module, "assess_estimated_gas", refuse_lower)
    sensitivity = interpretation_sensitivity(
        r.arterial_ph_estimate, r.arterial_paco2_estimate, r.provisional_interpretation
    )
    assert sensitivity["status"] == "INCOMPLETE"
    assert "No change" not in sensitivity["summary"]


@pytest.mark.parametrize(
    "ph,possible",
    [
        (7.349999, ["acidemia", "near-normal pH", "alkalemia"]),
        (7.35, ["near-normal pH", "alkalemia"]),
        (7.45, ["near-normal pH", "alkalemia"]),
        (7.450001, ["alkalemia"]),
    ],
)
def test_ph_conditional_boundaries_full_precision_and_single_axis(ph, possible):
    r = result(ph, None)
    assert r.physiology_direction["axes"]["ph"]["possibilities"] == possible
    if ph in (7.349999, 7.450001):
        assert "full precision" in r.physiology_direction["axes"]["ph"]["display_bound"]


@pytest.mark.parametrize("co2,n", [(39.999, 1), (40, 2), (40.001, 3)])
def test_co2_reference_is_not_a_screening_cutoff(co2, n):
    r = result(None, co2)
    assert len(r.physiology_direction["axes"]["pco2"]["possibilities"]) == n
    assert r.screening["status"] == "NOT_CONFIGURED"


def test_unreliable_axes_suppress_only_dependent_interpretation():
    # Simultaneous gas warnings must leave independent chemistry and finite estimates intact.
    blocked = {"ph", "pco2"}
    r = result(732, 1000, chemistry=CurrentChemistry(140, 100, 12))
    assert {o["field"] for o in r.input_observations if o["origin"] == "SUPPLIED"} == blocked
    for axis in ("ph", "pco2"):
        assert r.physiology_direction["axes"][axis]["status"] != "AVAILABLE"
    assert r.provisional_interpretation.status is Status.UNAVAILABLE_UNRELIABLE_INPUT
    assert r.chemistry["anion_gap"].values["anion_gap"] == 28
    assert r.arterial_ph_estimate.status is Status.AVAILABLE
    assert r.arterial_paco2_estimate.status is Status.AVAILABLE
    assert to_json(r)


def test_non_gas_warnings_preserve_usable_gas_interpretation_and_raw_arithmetic():
    r = result(
        hco3_mmol_l=101,
        base_excess_mmol_l=61,
        chemistry=CurrentChemistry(221, 201, 101, AlbuminInput(81, AlbuminUnit.G_L), 41),
    )
    assert len(r.input_observations) == 7
    assert r.provisional_interpretation.status is Status.AVAILABLE
    assert r.chemistry["anion_gap"].values["anion_gap"] == -81


def test_bmp_discrepancy_prefers_measured_pair_over_third_coordinate():
    r = result(7.36, 45, hco3_mmol_l=11, chemistry=CurrentChemistry(140, 100, 12))
    comparison = r.chemistry["bmp_gas_bicarbonate_comparison"]
    # The browser checks the comparator label, but not this contradictory-third-value arithmetic.
    assert comparison.values["bmp_minus_gas_hco3"] == pytest.approx(-13.430265200293658, abs=1e-6)


def test_albumin_units_normalize_once_and_never_guess():
    a, b = (
        CurrentChemistry(
            140,
            100,
            12,
            AlbuminInput(value, unit),
            relationship_to_vbg=Time.SAME_CLINICAL_TIMEPOINT,
        )
        for value, unit in [(4, AlbuminUnit.G_DL), (40, AlbuminUnit.G_L)]
    )
    assert result(chemistry=a).chemistry == result(chemistry=b).chemistry
    assert AlbuminInput(4, AlbuminUnit.G_L).normalized_g_l == 4
    overflow = result(
        chemistry=CurrentChemistry(140, 100, 12, AlbuminInput(1e308, AlbuminUnit.G_DL))
    )
    assert overflow.chemistry["corrected_anion_gap"].status is Status.MODEL_DOMAIN_REFUSAL
    assert to_json(overflow)


def test_farkas_point_and_interval_outside_direction_are_retained():
    r = result(sat=100)
    assert r.arterial_paco2_estimate.values["point"] == pytest.approx(56.54)
    assert r.arterial_paco2_estimate.agreement.upper == pytest.approx(65.28)


def test_pinned_adapter_rejects_unknown_template():
    # Browser scenarios cannot simulate a changed template in the pinned upstream helper.
    raw = to_primitive(assess_boston(_EstimatedGas(7.5, 90, 50)))
    raw["measured_vs_expected"] = "unrecognized changed upstream template"
    with pytest.raises(ValueError):
        _adapt_assessment(raw)
