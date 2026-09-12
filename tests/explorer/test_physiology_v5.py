"""Synthetic v0.5 acceptance gates, including failure propagation and source boundaries."""

from dataclasses import replace

import pytest
from stewartlight.interpret import assess_boston
from test_foundation import wire_request

from vbg_interpreter import interpret_vbg, request_from_mapping
from vbg_interpreter.best_guess import (
    _adapt_assessment,
    _EstimatedGas,
    assess_estimated_gas,
    interpretation_sensitivity,
    modeled_hco3,
)
from vbg_interpreter.chemistry import calculate_chemistry
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
from vbg_interpreter.observations import LIMITS, input_observations
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


@pytest.mark.parametrize("sample", list(SampleType))
@pytest.mark.parametrize("sat", [None, 75])
def test_sample_selection_and_no_hidden_fallback(sample, sat):
    r = result(sample=sample, sat=sat)
    farkas = sample is SampleType.PERIPHERAL and sat is not None
    assert r.arterial_ph_estimate.values["ph"] == pytest.approx(7.36)
    assert r.arterial_paco2_estimate.values["point"] == pytest.approx(51.04 if farkas else 50)
    assert ("lower" in r.arterial_paco2_estimate.values) == farkas
    assert ("not used" in r.narrative["best_guess"]) == (sat is not None and not farkas)
    if sample is SampleType.UNKNOWN:
        assert "illustrative systemic-venous" in r.narrative["conditional_physiology"]
        assert "Sample type not specified." in r.physiology_direction["caption"]


def test_sensitivity_recomputes_hh_and_exposes_changed_compensation():
    r = result(7.21, 29, sat=75)
    assert r.interpretation_sensitivity["status"] == "CHANGES"
    scenarios = r.interpretation_sensitivity["scenarios"]
    assert [s["pco2"] for s in scenarios] == pytest.approx([15.84, 25.04, 33.78], abs=1e-6)
    assert [s["hco3"] for s in scenarios] == pytest.approx(
        [6.948539852964475, 10.984307949383236, 14.818287640981062], abs=1e-6
    )
    assert [s["assessment"]["compensation_category"] for s in scenarios] == [
        "BELOW",
        "WITHIN",
        "ABOVE",
    ]
    assert [
        s["assessment"]["expected_compensation"]["lower_mmhg"] for s in scenarios
    ] == pytest.approx([16.422809779, 22.476461924, 28.227431461], abs=1e-6)
    assert "not robust" in r.narrative["best_guess"]


def test_unchanged_scenarios_are_not_called_full_robustness():
    r = result(7.10, 100, sat=75)
    assert r.interpretation_sensitivity["status"] == "NO_CHANGE_TESTED"
    assert r.interpretation_sensitivity["summary"] == (
        "No change in the tested CO₂ scenarios; pH uncertainty and full "
        "robustness remain unassessed."
    )
    assert result().interpretation_sensitivity["status"] == "NOT_QUANTIFIED"


def test_failed_sensitivity_scenario_never_claims_robustness(monkeypatch):
    import vbg_interpreter.best_guess as module

    r = result(sat=75)
    original = module.assess_estimated_gas

    def refuse_lower(ph, co2, hco3):
        assessment = original(ph, co2, hco3)
        return (
            replace(assessment, status=Status.MODEL_DOMAIN_REFUSAL)
            if co2.values["point"] == co2.values["lower"]
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
        (7.46, ["alkalemia"]),
    ],
)
def test_ph_conditional_boundaries_full_precision_and_single_axis(ph, possible):
    r = result(ph, None)
    assert r.physiology_direction["axes"]["ph"]["possibilities"] == possible
    assert r.physiology_direction["axes"]["pco2"]["bound"] is None
    assert r.provisional_interpretation.status is Status.UNAVAILABLE_MISSING_INPUT
    if ph in (7.349999, 7.450001):
        assert "full precision" in r.physiology_direction["axes"]["ph"]["display_bound"]
    assert "no upper pH bound" in r.physiology_direction["summary"]


@pytest.mark.parametrize("co2,n", [(30, 1), (39.999, 1), (40, 2), (40.001, 3), (55, 3)])
def test_co2_reference_is_not_a_screening_cutoff(co2, n):
    r = result(None, co2)
    assert len(r.physiology_direction["axes"]["pco2"]["possibilities"]) == n
    assert r.physiology_direction["axes"]["ph"]["bound"] is None
    assert r.screening["status"] == "NOT_CONFIGURED"


def test_supplied_or_hh_derived_coordinates_never_become_independent_bounds():
    r = result(None, 55, hco3_mmol_l=27)
    assert r.venous_gas.calculated_values["ph"].status is Status.AVAILABLE
    assert r.physiology_direction["axes"]["ph"]["bound"] is None
    assert "Measured venous pH" in r.highest_value_next_inputs[0]
    r = result(7.32, None, hco3_mmol_l=27)
    assert r.physiology_direction["axes"]["pco2"]["bound"] is None
    assert "Measured PvCO2" in r.highest_value_next_inputs[0]


@pytest.mark.parametrize(
    "ph,co2,blocked", [(732, 55, {"ph"}), (7.32, 1000, {"pco2"}), (732, 1000, {"ph", "pco2"})]
)
def test_unreliable_axes_suppress_only_dependent_interpretation(ph, co2, blocked):
    r = result(ph, co2, chemistry=CurrentChemistry(140, 100, 12))
    assert {o["field"] for o in r.input_observations} == blocked
    for axis in ("ph", "pco2"):
        assert (r.physiology_direction["axes"][axis]["status"] == "AVAILABLE") == (
            axis not in blocked
        )
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


@pytest.mark.parametrize("field", list(LIMITS))
def test_sanity_policy_includes_exact_endpoints(field):
    low, high, _ = LIMITS[field]
    for value in (low, high):
        source = CurrentVbg(ph=7.32, pco2=55, pco2_unit=Pco2Unit.MMHG)
        chem = CurrentChemistry()
        if field in ["ph", "pco2", "hco3", "base_excess"]:
            name = {"hco3": "hco3_mmol_l", "base_excess": "base_excess_mmol_l"}.get(field, field)
            source = replace(source, **{name: value})
        else:
            name = {
                "bmp_hco3": "serum_total_co2_mmol_l",
                "sodium": "sodium_mmol_l",
                "chloride": "chloride_mmol_l",
                "lactate": "lactate_mmol_l",
                "albumin": "albumin",
            }[field]
            chem = replace(
                chem,
                **{name: AlbuminInput(value, AlbuminUnit.G_L) if field == "albumin" else value},
            )
        assert not any(
            o["field"] == field for o in input_observations(VbgExplorerRequest(source, chem))
        )


def test_bmp_discrepancy_prefers_measured_pair_and_preserves_third_coordinate():
    r = result(7.36, 45, hco3_mmol_l=11, chemistry=CurrentChemistry(140, 100, 12))
    comparison = r.chemistry["bmp_gas_bicarbonate_comparison"]
    assert comparison.values["gas_basis_hco3"] == pytest.approx(25.430265200293658, abs=1e-6)
    assert comparison.values["bmp_minus_gas_hco3"] == pytest.approx(-13.430265200293658, abs=1e-6)
    assert r.venous_gas.measured_values["hco3"]["value"] == 11
    assert "Large discrepancy" in r.narrative["best_guess"]
    assert r.chemistry["anion_gap"].values["anion_gap"] == 28


@pytest.mark.parametrize("ph,co2", [(7.32, None), (None, 55)])
def test_bmp_alternate_completed_pair_basis_is_explicit(ph, co2):
    r = result(ph, co2, hco3_mmol_l=27, chemistry=CurrentChemistry(140, 100, 12))
    c = r.chemistry["bmp_gas_bicarbonate_comparison"]
    assert c.values["gas_basis"] == "SUPPLIED_BLOOD_GAS_HCO3_COMPLETED_PAIR"
    assert c.values["bmp_minus_gas_hco3"] == -15


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
    req = VbgExplorerRequest(CurrentVbg(ph=7.32), a)
    assert request_from_mapping(wire_request(req)) == req
    assert req.to_dict()["current_chemistry"]["albumin"] == {
        "value": 4,
        "unit": "g/dL",
        "normalized_g_l": 40,
    }
    assert AlbuminInput(4, AlbuminUnit.G_L).normalized_g_l == 4
    overflow = result(
        chemistry=CurrentChemistry(140, 100, 12, AlbuminInput(1e308, AlbuminUnit.G_DL))
    )
    assert overflow.chemistry["corrected_anion_gap"].status is Status.MODEL_DOMAIN_REFUSAL
    assert to_json(overflow)


def test_farkas_point_and_interval_outside_direction_are_retained():
    r = result(sat=100)
    assert r.arterial_paco2_estimate.values["point"] == pytest.approx(56.54)
    assert r.arterial_paco2_estimate.values["upper"] == pytest.approx(65.28)
    assert r.physiology_direction["axes"]["pco2"]["bound"] == 55
    assert len(r.narrative["model_disagreements"]) == 2


@pytest.mark.parametrize("status", [s for s in Status if s is not Status.AVAILABLE])
@pytest.mark.parametrize("axis", ["ph", "co2", "hco3"])
def test_every_dependency_failure_is_propagated_before_dereference(status, axis):
    r = result()
    ph, co2, hco3 = r.arterial_ph_estimate, r.arterial_paco2_estimate, r.modeled_arterial_hco3
    values = {"ph": ph, "co2": co2, "hco3": hco3}
    values[axis] = replace(values[axis], status=status, values={})
    assert assess_estimated_gas(**values).status is status
    if axis != "hco3":
        assert modeled_hco3(values["ph"], values["co2"]).status is status
    req = VbgExplorerRequest(
        CurrentVbg(ph=7.32),
        CurrentChemistry(
            140,
            105,
            24,
            AlbuminInput(40, AlbuminUnit.G_L),
            relationship_to_vbg=Time.SAME_CLINICAL_TIMEPOINT,
        ),
    )
    gas = replace(
        r.venous_gas,
        standard_base_excess=replace(r.venous_gas.standard_base_excess, status=status, values={}),
    )
    assert calculate_chemistry(req, gas)["venous_stewart_partition"].status is status


def test_pinned_adapter_rejects_unknown_template_and_keeps_structured_oracle():
    for ph in (7.2, 7.4, 7.5):
        for co2 in (10, 25, 40, 60, 90):
            for hco3 in (10, 20, 24, 30, 50):
                raw = to_primitive(assess_boston(_EstimatedGas(ph, co2, hco3)))
                adapted = _adapt_assessment(dict(raw))
                assert adapted["expected_compensation"] == raw["expected_compensation"]
                assert adapted["mixed_disorder_flag"] == raw["mixed_disorder_flag"]
    raw["measured_vs_expected"] = "unrecognized changed upstream template"
    with pytest.raises(ValueError):
        _adapt_assessment(raw)
