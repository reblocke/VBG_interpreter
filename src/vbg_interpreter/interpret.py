"""One input-adaptive interpretation entry point."""

from copy import deepcopy

from vbg_interpreter.arterial_paco2 import estimate_arterial_paco2
from vbg_interpreter.chemistry import calculate_chemistry
from vbg_interpreter.evidence import METHODS
from vbg_interpreter.information import highest_value_next_inputs
from vbg_interpreter.models import CalculationStatus, VbgExplorerRequest, VbgExplorerResult
from vbg_interpreter.screening import screening_result
from vbg_interpreter.venous_gas import complete_venous_gas


def interpret_vbg(request: VbgExplorerRequest) -> VbgExplorerResult:
    if not isinstance(request, VbgExplorerRequest):
        raise TypeError("request must be VbgExplorerRequest.")
    gas = complete_venous_gas(request.current_vbg)
    chemistry = calculate_chemistry(request, gas)
    estimate = estimate_arterial_paco2(request)
    unresolved = [
        "Arterial pH, arterial oxygenation, and a complete arterial acid–base "
        "interpretation are not established."
    ]
    if estimate.status is not CalculationStatus.AVAILABLE:
        unresolved.append(
            "PaCO2 estimation is unavailable from the supplied measurements and context."
        )
    elif estimate.applicability == "APPLICABILITY_UNCERTAIN":
        unresolved.append("The PaCO2 estimate has uncertain applicability to the supplied context.")
    if any(
        c.status is CalculationStatus.MODEL_DOMAIN_REFUSAL
        for c in (*gas.calculated_values.values(), gas.standard_base_excess, *chemistry.values())
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
        unresolved_questions=tuple(unresolved),
        highest_value_next_inputs=highest_value_next_inputs(request, gas, chemistry, estimate),
        methods=deepcopy(METHODS),
    )
