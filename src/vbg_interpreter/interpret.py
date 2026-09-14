"""One input-adaptive interpretation entry point."""

from copy import deepcopy
from dataclasses import replace

from vbg_interpreter.arterial_paco2 import estimate_arterial_paco2, estimate_arterial_ph
from vbg_interpreter.best_guess import (
    assess_estimated_gas,
    interpretation_sensitivity,
    modeled_hco3,
)
from vbg_interpreter.chemistry import bicarbonate_comparison, calculate_chemistry
from vbg_interpreter.evidence import METHODS
from vbg_interpreter.information import highest_value_next_inputs
from vbg_interpreter.models import CalculationStatus, VbgExplorerRequest, VbgExplorerResult
from vbg_interpreter.narrative import build_narrative
from vbg_interpreter.observations import gas_observations, qualify_calculation, unreliable_axes
from vbg_interpreter.physiology import direction_metadata
from vbg_interpreter.screening import screening_result
from vbg_interpreter.venous_gas import complete_venous_gas


def interpret_vbg(request: VbgExplorerRequest) -> VbgExplorerResult:
    if not isinstance(request, VbgExplorerRequest):
        raise TypeError("request must be VbgExplorerRequest.")
    gas = complete_venous_gas(request.current_vbg)
    observations = gas_observations(request, gas)
    gas = replace(
        gas,
        calculated_values={
            k: qualify_calculation(c, observations, output_axis=k)
            for k, c in gas.calculated_values.items()
        },
        consistency=qualify_calculation(gas.consistency, observations, output_axis="hco3"),
        standard_base_excess=qualify_calculation(gas.standard_base_excess, observations),
    )
    chemistry = calculate_chemistry(request, gas)
    blocked = unreliable_axes(observations)
    estimate = estimate_arterial_paco2(request, gas, observations)
    ph = estimate_arterial_ph(request, gas, observations)
    hco3 = modeled_hco3(ph, estimate)
    direction = direction_metadata(request, observations)
    if "ph" in blocked:
        gas = replace(gas, ph_reference_position=None)
    chemistry["bmp_gas_bicarbonate_comparison"] = bicarbonate_comparison(request, blocked)
    chemistry = {k: qualify_calculation(c, observations) for k, c in chemistry.items()}
    hco3 = replace(
        hco3,
        input_warnings=tuple(
            o for o in observations if o in ph.input_warnings or o in estimate.input_warnings
        ),
    )
    interpretation_ph = (
        replace(ph, status=CalculationStatus.UNAVAILABLE_UNRELIABLE_INPUT)
        if ph.status is CalculationStatus.AVAILABLE and not ph.selection.interpretation_suitable
        else ph
    )
    interpretation_co2 = (
        replace(estimate, status=CalculationStatus.UNAVAILABLE_UNRELIABLE_INPUT)
        if estimate.status is CalculationStatus.AVAILABLE
        and not estimate.selection.interpretation_suitable
        else estimate
    )
    provisional = assess_estimated_gas(interpretation_ph, interpretation_co2, hco3)
    sensitivity = interpretation_sensitivity(interpretation_ph, interpretation_co2, provisional)
    narrative = build_narrative(
        request,
        ph,
        estimate,
        provisional,
        sensitivity,
        direction,
        chemistry["bmp_gas_bicarbonate_comparison"],
    )
    unresolved = [
        "Arterial pH, arterial oxygenation, and a complete arterial acid–base "
        "interpretation are not established."
    ]
    if estimate.status is not CalculationStatus.AVAILABLE:
        unresolved.append(
            "PaCO2 estimation is unavailable from the supplied measurements and context."
        )
    if any(
        c.status is CalculationStatus.MODEL_DOMAIN_REFUSAL
        for c in (
            *gas.calculated_values.values(),
            gas.standard_base_excess,
            *chemistry.values(),
            ph,
            estimate,
            hco3,
        )
    ):
        unresolved.append(
            "A calculation exceeded its numerical domain; other supported results remain available."
        )
    return VbgExplorerResult(
        input_summary=request.to_dict(),
        venous_gas=gas,
        chemistry=chemistry,
        screening=screening_result(),
        arterial_paco2_estimate=estimate,
        arterial_ph_estimate=ph,
        modeled_arterial_hco3=hco3,
        provisional_interpretation=provisional,
        unresolved_questions=tuple(unresolved),
        highest_value_next_inputs=highest_value_next_inputs(request, chemistry, ph, estimate),
        methods=deepcopy(METHODS),
        input_observations=observations,
        physiology_direction=direction,
        interpretation_sensitivity=sensitivity,
        narrative=narrative,
    )
