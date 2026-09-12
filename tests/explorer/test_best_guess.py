"""Synthetic regressions for the approved estimates and gas-only interpretation."""

from dataclasses import fields, replace

import pytest
from stewartlight.interpret import assess_boston
from stewartlight.models import AcidBaseInput
from test_foundation import wire_request

from vbg_interpreter import interpret_vbg
from vbg_interpreter.best_guess import _EstimatedGas
from vbg_interpreter.mapping import request_from_mapping
from vbg_interpreter.models import (
    BaseExcessBasis,
    CurrentVbg,
    Pco2Unit,
    SaturationInput,
    SaturationUnit,
    VbgExplorerRequest,
)
from vbg_interpreter.models import (
    CalculationStatus as Status,
)
from vbg_interpreter.serialization import ExplorerSerializationError


def gas_result(ph=7.32, pco2=55, **changes):
    return interpret_vbg(
        VbgExplorerRequest(
            CurrentVbg(
                ph=ph, pco2=pco2, pco2_unit=None if pco2 is None else Pco2Unit.MMHG, **changes
            )
        )
    )


def test_pair_without_be_or_saturation_returns_estimates_and_interpretation():
    r = gas_result()
    assert r.arterial_ph_estimate.values == {"ph": 7.36}
    assert r.arterial_paco2_estimate.values["point"] == 50
    assert set(r.arterial_paco2_estimate.values) == {"point", "measured_pvco2"}
    assert r.arterial_paco2_estimate.method_id == "fixed_paco2_offset_v1"
    assert r.modeled_arterial_hco3.values["modeled_hco3"] == pytest.approx(28.25585022254851)
    assert r.provisional_interpretation.status is Status.AVAILABLE
    assert (
        "mixed process possible" in r.provisional_interpretation.assessment["primary_process_guess"]
    )
    assert r.venous_gas.measured_values["ph"]["value"] == 7.32
    assert r.venous_gas.calculated_values["hco3"].values["hco3"] == pytest.approx(28.34660584599947)


def test_saturation_selects_farkas_without_second_correction_or_ph_change():
    r = gas_result(venous_o2_saturation=SaturationInput(75, SaturationUnit.PERCENTAGE_POINTS))
    assert r.arterial_ph_estimate.values == {"ph": 7.36}
    assert r.arterial_paco2_estimate.values["point"] == pytest.approx(51.04)
    assert r.arterial_paco2_estimate.values["lower"] == pytest.approx(41.84)
    assert r.arterial_paco2_estimate.values["upper"] == pytest.approx(59.78)
    assert r.arterial_paco2_estimate.applicability == "APPLICABILITY_UNASSESSED"
    assert r.arterial_paco2_estimate.method_id == "farkas_simplified_93_v1"


@pytest.mark.parametrize(
    "saturation", [None, SaturationInput(0.75, SaturationUnit.FRACTION_0_TO_1)]
)
def test_pressure_units_preserve_both_measured_display_and_estimate(saturation):
    mm = CurrentVbg(ph=7.32, pco2=55, pco2_unit=Pco2Unit.MMHG, venous_o2_saturation=saturation)
    kpa = replace(mm, pco2=55 / 7.500616827041697, pco2_unit=Pco2Unit.KPA)
    a, b = (interpret_vbg(VbgExplorerRequest(g)) for g in (mm, kpa))
    assert a.arterial_paco2_estimate.values == pytest.approx(b.arterial_paco2_estimate.values)
    assert b.venous_gas.measured_values["pco2"]["value"] == kpa.pco2
    assert b.venous_gas.measured_values["pco2"]["normalized_mmhg"] == pytest.approx(55)


@pytest.mark.parametrize("ph,pco2", [(7.32, None), (None, 55)])
def test_single_coordinate_remains_available_without_full_interpretation(ph, pco2):
    r = gas_result(ph, pco2)
    assert (r.arterial_ph_estimate.status is Status.AVAILABLE) == (ph is not None)
    assert (r.arterial_paco2_estimate.status is Status.AVAILABLE) == (pco2 is not None)
    assert r.provisional_interpretation.status is Status.UNAVAILABLE_MISSING_INPUT


def test_hh_derived_ph_does_not_become_a_measured_estimation_input():
    r = gas_result(None, 55, hco3_mmol_l=27)
    assert r.venous_gas.calculated_values["ph"].status is Status.AVAILABLE
    assert r.arterial_ph_estimate.status is Status.UNAVAILABLE_MISSING_INPUT
    assert r.provisional_interpretation.status is Status.UNAVAILABLE_MISSING_INPUT


@pytest.mark.parametrize("be", [None, -8, 0, 8])
def test_be_is_independent_of_best_guess(be):
    r = gas_result(
        base_excess_mmol_l=be,
        base_excess_basis=BaseExcessBasis.UNKNOWN if be is None else BaseExcessBasis.STANDARD,
    )
    base = gas_result()
    assert r.arterial_ph_estimate == base.arterial_ph_estimate
    assert r.arterial_paco2_estimate == base.arterial_paco2_estimate
    assert r.provisional_interpretation == base.provisional_interpretation


@pytest.mark.parametrize("pco2", [1, 5])
def test_invalid_fixed_estimate_is_local_refusal_not_clamped(pco2):
    r = gas_result(pco2=pco2)
    assert r.arterial_paco2_estimate.status is Status.MODEL_DOMAIN_REFUSAL
    assert r.arterial_paco2_estimate.values == {}
    assert r.arterial_ph_estimate.values == {"ph": 7.36}
    assert r.provisional_interpretation.status is Status.MODEL_DOMAIN_REFUSAL


def test_invalid_farkas_range_never_silently_falls_back_to_fixed():
    r = gas_result(
        pco2=10, venous_o2_saturation=SaturationInput(75, SaturationUnit.PERCENTAGE_POINTS)
    )
    assert r.arterial_paco2_estimate.status is Status.MODEL_DOMAIN_REFUSAL
    assert r.arterial_paco2_estimate.method_id == "farkas_simplified_93_v1"


def test_modeled_hco3_overflow_keeps_ph_and_co2_estimates():
    r = gas_result(ph=400)
    assert r.modeled_arterial_hco3.status is Status.MODEL_DOMAIN_REFUSAL
    assert r.provisional_interpretation.status is Status.MODEL_DOMAIN_REFUSAL
    assert r.arterial_ph_estimate.status is Status.AVAILABLE
    assert r.arterial_paco2_estimate.status is Status.AVAILABLE


@pytest.mark.parametrize(
    "ph,co2,hco3",
    [
        (7.2, 25, 12),
        (7.2, 50, 12),
        (7.2, 10, 12),  # Winter within/above/below
        (7.5, 50, 36),
        (7.5, 70, 36),
        (7.5, 25, 36),  # metabolic alkalosis
        (7.2, 60, 25),
        (7.2, 60, 40),
        (7.2, 60, 23),  # respiratory acidosis
        (7.5, 25, 22),
        (7.5, 25, 15),
        (7.5, 25, 26),  # respiratory alkalosis
        (7.35, 40, 24),
        (7.45, 40, 24),
        (7.349, 40, 24),
        (7.451, 40, 24),
        (7.4, 50, 28),
        (7.4, 30, 20),
    ],
)
def test_gas_only_adapter_preserves_pinned_upstream_rules(ph, co2, hco3):
    # Synthetic full inputs are oracle fixtures, never constructed by the Explorer adapter.
    full = AcidBaseInput(ph, co2, hco3, 0, 140, 105, 40)
    assert assess_boston(_EstimatedGas(ph, co2, hco3)) == assess_boston(full)
    assert {f.name for f in fields(_EstimatedGas)} == {
        "ph",
        "pco2_mmhg",
        "hco3_mmol_l",
        "suspect_chronic_hypercapnia",
    }


@pytest.mark.parametrize("ph,pco2", [(7.16, 35), (7.46, 55), (7.16, 65), (7.46, 25), (7.36, 45)])
def test_renderable_interpretation_never_calls_estimated_operands_measured(ph, pco2):
    r = gas_result(ph, pco2)
    assert r.provisional_interpretation.status is Status.AVAILABLE
    assert "measured" not in str(r.provisional_interpretation.assessment).lower()
    assert "chronicity" in " ".join(r.provisional_interpretation.limitations)


@pytest.mark.parametrize("field", ["specimen_type", "draw_site", "saturation_same_sample"])
def test_removed_questionnaire_fields_are_rejected_in_v4(field):
    data = wire_request()
    data["current_vbg"][field] = "UNKNOWN"
    with pytest.raises(ExplorerSerializationError):
        request_from_mapping(data)
