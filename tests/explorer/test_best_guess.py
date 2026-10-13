"""Synthetic regressions for the approved estimates and gas-only interpretation."""

import pytest
from stewartlight.interpret import assess_boston
from stewartlight.models import AcidBaseInput

from vbg_interpreter import interpret_vbg
from vbg_interpreter.best_guess import _EstimatedGas
from vbg_interpreter.models import (
    BaseExcessBasis,
    CurrentVbg,
    Pco2Unit,
    SampleType,
    VbgExplorerRequest,
)
from vbg_interpreter.models import (
    CalculationStatus as Status,
)


def gas_result(ph=7.32, pco2=55, **changes):
    changes.setdefault("sample_type", SampleType.PERIPHERAL)
    return interpret_vbg(
        VbgExplorerRequest(
            CurrentVbg(
                ph=ph, pco2=pco2, pco2_unit=None if pco2 is None else Pco2Unit.MMHG, **changes
            )
        )
    )


def test_modeled_bicarbonate_and_interpretation_use_estimated_pair():
    r = gas_result()
    assert r.modeled_arterial_hco3.values["modeled_hco3"] == pytest.approx(28.25585022254851)
    assert (
        "mixed process possible" in r.provisional_interpretation.assessment["primary_process_guess"]
    )


@pytest.mark.parametrize("be", [-8, 0])
def test_be_is_independent_of_best_guess(be):
    r = gas_result(
        base_excess_mmol_l=be,
        base_excess_basis=BaseExcessBasis.STANDARD,
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


def test_modeled_hco3_overflow_keeps_ph_and_co2_estimates():
    r = gas_result(ph=400)
    assert r.modeled_arterial_hco3.status is Status.MODEL_DOMAIN_REFUSAL
    assert r.provisional_interpretation.status is Status.UNAVAILABLE_UNRELIABLE_INPUT
    assert r.arterial_ph_estimate.status is Status.AVAILABLE
    assert r.arterial_paco2_estimate.status is Status.AVAILABLE


def test_gas_only_adapter_does_not_assume_chronic_hypercapnia():
    # An accidental True default narrows compensation to chronic-only; live E2E misses this branch.
    full = AcidBaseInput(7.2, 60, 25, 0, 140, 105, 40)
    assert assess_boston(_EstimatedGas(7.2, 60, 25)) == assess_boston(full)


@pytest.mark.parametrize("ph,pco2", [(7.16, 35), (7.46, 55), (7.16, 65), (7.46, 25), (7.36, 45)])
def test_renderable_interpretation_never_calls_estimated_operands_measured(ph, pco2):
    r = gas_result(ph, pco2)
    assert r.provisional_interpretation.status is Status.AVAILABLE
    assert "measured" not in str(r.provisional_interpretation.assessment).lower()
    assert "chronicity" in " ".join(r.provisional_interpretation.limitations)
