"""Per-output arterial estimates with explicit source chains and unassessed applicability."""

import math
from dataclasses import replace

from vbg_interpreter.evidence import PACO2_CONSERVATIVE_ERRORS, calculation
from vbg_interpreter.models import Agreement, Calculation, CalculationStatus, VbgExplorerRequest
from vbg_interpreter.observations import component_warnings, gas_observations
from vbg_interpreter.selection import route_label, select_component
from vbg_interpreter.venous_gas import complete_venous_gas

APPLICABILITY = "APPLICABILITY_UNASSESSED"
CONTEXT_LIMIT = (
    "Applicability is unassessed. Venous–arterial differences vary with sampling, "
    "perfusion and clinical state; these estimates do not establish arterial measurements."
)


def _estimate(request, axis, gas, observations):
    if gas is None:
        gas = complete_venous_gas(request.current_vbg)
    if observations is None:
        observations = gas_observations(request, gas)
    method, selection = select_component(request.current_vbg, gas, axis)
    warnings = component_warnings(observations, axis, selection)
    selection = replace(
        selection,
        interpretation_suitable=selection.interpretation_suitable and not warnings,
        reason_codes=(
            *selection.reason_codes,
            *(("DEPENDENCY_SANITY_WARNING",) if warnings else ()),
        ),
    )
    chained = selection.case_evidence == "CHAINED_UNVALIDATED"
    farkas = method == "farkas_simplified_93_v1"
    limits = [CONTEXT_LIMIT]
    if axis == "ph":
        limits.append("Rough fixed pH correction (+0.04); no individual uncertainty interval.")
    elif not farkas:
        limits.append("Rough fixed CO2 correction (−5 mmHg); no individual uncertainty interval.")
    else:
        limits.append(
            "Farkas PaCO2 component externally evaluated in peripheral samples; this combined "
            "pH/CO2 interpretation is not externally validated."
        )
    if selection.model_scope == "PERIPHERAL_ASSUMPTION":
        limits.append("Farkas estimate assumes a peripheral sample; sample type is unknown.")
    elif selection.model_scope == "CENTRAL_HEURISTIC":
        limits.append(
            "Central sample: the fixed CO2 heuristic is used; peripheral Farkas was not applied."
        )
    if chained:
        name = "pH" if axis == "ph" else "PvCO2"
        limits.append(
            f"Best guess using an HH-reconstructed venous {name}. Chained route is unvalidated."
        )
    agreement = Agreement("NOT_QUANTIFIED", "NO_EVALUATED_INTERVAL")
    values, units = {}, {}
    failed = selection.source_status is CalculationStatus.MODEL_DOMAIN_REFUSAL
    if selection.source_value is not None:
        source_value = selection.source_value
        try:
            if axis == "ph":
                point = source_value + 0.04
                values, units = {"ph": point}, {"ph": "pH units"}
            else:
                saturation = request.current_vbg.venous_o2_saturation
                point = source_value - (
                    0.22 * (93 - saturation.normalized_percentage_points) if farkas else 5
                )
                values = {"source_pvco2": source_value, "point": point}
                units = {"source_pvco2": "mmHg", "point": "mmHg"}
                if farkas:
                    values["saturation_percent"] = saturation.normalized_percentage_points
                    units["saturation_percent"] = "%"
                    if saturation.normalized_percentage_points > 93:
                        limits.append(
                            "Saturation exceeds the simplified 93% reference; no clamp applied."
                        )
            failed = not math.isfinite(point) or point <= 0
            if failed:
                agreement = Agreement("UNAVAILABLE", "POINT_UNAVAILABLE")
            elif farkas and chained:
                agreement = Agreement("NOT_QUANTIFIED", "RECONSTRUCTED_PVCO2_CHAIN")
                limits.append(
                    "Uncertainty for the reconstructed-PvCO2 chain has not been quantified."
                )
            elif farkas:
                error_lower, error_upper = PACO2_CONSERVATIVE_ERRORS
                lower, upper = point - error_upper, point - error_lower
                if all(math.isfinite(v) and v > 0 for v in (lower, upper)):
                    agreement = Agreement("AVAILABLE", "PERIPHERAL_STUDY_COMPARISON", lower, upper)
                    limits.append(
                        "Conservative published peripheral-study agreement range; not a "
                        "patient-specific confidence interval or joint pH/CO2 region."
                    )
                    if selection.model_scope == "PERIPHERAL_ASSUMPTION":
                        limits.append(
                            "Agreement is peripheral-study context under an unconfirmed sample "
                            "assumption."
                        )
                else:
                    agreement = Agreement("UNAVAILABLE", "NONPHYSICAL_ENDPOINT")
                    limits.append(
                        "Agreement interval is nonphysical and unavailable; the finite point "
                        "is retained with a numerical/spectrum limitation."
                    )
        except (ArithmeticError, ValueError):
            failed = True
            agreement = Agreement("UNAVAILABLE", "POINT_UNAVAILABLE")
    else:
        agreement = Agreement("UNAVAILABLE", "POINT_UNAVAILABLE")
    result = calculation(
        method,
        values=values,
        units=units,
        origins={key: str(entry["provenance"]) for key, entry in selection.source_values.items()},
        missing=("usable venous " + ("pH" if axis == "ph" else "PvCO2"),)
        if selection.source_status is CalculationStatus.UNAVAILABLE_MISSING_INPUT
        else (),
        domain_refusal=failed,
        provenance="CHAINED_ARTERIAL_ESTIMATE"
        if chained
        else "MODEL_BASED_ARTERIAL_ESTIMATE"
        if farkas
        else "HEURISTIC_ARTERIAL_ESTIMATE",
        applicability=APPLICABILITY,
        limitations=tuple(limits),
    )
    if result.status is CalculationStatus.MODEL_DOMAIN_REFUSAL:
        selection = replace(
            selection, reason_codes=(*selection.reason_codes, "SELECTED_METHOD_NUMERICAL_FAILURE")
        )
    selection = replace(
        selection,
        interpretation_suitable=selection.interpretation_suitable
        and result.status is CalculationStatus.AVAILABLE,
    )
    result = replace(result, selection=selection, agreement=agreement, input_warnings=warnings)
    return replace(result, route_label=route_label(result))


def estimate_arterial_ph(request: VbgExplorerRequest, gas=None, observations=None) -> Calculation:
    return _estimate(request, "ph", gas, observations)


def estimate_arterial_paco2(
    request: VbgExplorerRequest, gas=None, observations=None
) -> Calculation:
    return _estimate(request, "pco2", gas, observations)
