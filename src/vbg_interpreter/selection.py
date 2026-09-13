"""Pure per-component selection from supplied or already HH-completed venous inputs."""

from copy import deepcopy
from typing import Literal

from vbg_interpreter.models import (
    ArterialSelection,
    CalculationStatus,
    CurrentVbg,
    SampleType,
    VenousGas,
)


def select_component(
    source: CurrentVbg, gas: VenousGas, axis: Literal["ph", "pco2"], blocked: set[str]
) -> tuple[str, ArterialSelection]:
    supplied = getattr(source, axis) is not None
    fields = (axis,) if supplied else ("pco2", "hco3") if axis == "ph" else ("ph", "hco3")
    inputs = {
        key: deepcopy(gas.measured_values[key]) for key in fields if key in gas.measured_values
    }
    value = None
    if supplied:
        measurement = inputs[axis]
        value = measurement.get("normalized_mmhg") if axis == "pco2" else measurement["value"]
        status = (
            CalculationStatus.AVAILABLE
            if value is not None
            else CalculationStatus.MODEL_DOMAIN_REFUSAL
        )
    else:
        completed = gas.calculated_values[axis]
        status = completed.status
        value = completed.values.get(axis)
    origin = "SUPPLIED" if supplied else "HH_RECONSTRUCTED" if value is not None else "UNAVAILABLE"
    method, scope = "fixed_ph_offset_v1", "UNASSESSED"
    reasons = ["PH_FIXED_HEURISTIC" if supplied else "PH_FIXED_FROM_RECONSTRUCTED_VENOUS_PH"]
    if axis == "pco2":
        if source.sample_type is SampleType.CENTRAL:
            method, scope, reasons = (
                "fixed_paco2_offset_v1",
                "CENTRAL_HEURISTIC",
                ["FIXED_CENTRAL_SAMPLE"],
            )
        elif source.venous_o2_saturation is None:
            method, reasons = "fixed_paco2_offset_v1", ["FIXED_SATURATION_NOT_SUPPLIED"]
        else:
            method = "farkas_simplified_93_v1"
            reasons = [
                "FARKAS_SUPPLIED_PVCO2_AND_SATURATION"
                if supplied
                else "FARKAS_RECONSTRUCTED_PVCO2_CHAIN"
            ]
            scope = "PERIPHERAL_CATEGORY_MATCH"
            if source.sample_type is SampleType.UNKNOWN:
                scope = "PERIPHERAL_ASSUMPTION"
                reasons.append("FARKAS_UNKNOWN_SAMPLE_PERIPHERAL_ASSUMPTION")
            inputs["venous_saturation"] = deepcopy(gas.measured_values["venous_saturation"])
    if value is None:
        reasons = [
            r
            for r in reasons
            if r
            not in ("PH_FIXED_FROM_RECONSTRUCTED_VENOUS_PH", "FARKAS_RECONSTRUCTED_PVCO2_CHAIN")
        ]
        reasons.append("NO_USABLE_VENOUS_COORDINATE")
    return method, ArterialSelection(
        source_coordinate_origin=origin,
        source_value=value,
        source_status=status,
        source_field_ids=tuple(inputs),
        source_values=inputs,
        derivation_method_id=None
        if supplied
        else "henderson_hasselbalch_v1"
        if value is not None
        else None,
        sample_type_as_entered=source.sample_type,
        model_scope=scope,
        reason_codes=tuple(reasons),
        case_evidence="SUPPLIED_INPUT"
        if supplied
        else "CHAINED_UNVALIDATED"
        if value is not None
        else "UNAVAILABLE",
        # Only supplied pH/PCO2 warnings suppress dependent interpretation. HCO3 warnings do not.
        interpretation_suitable=value is not None and not blocked.intersection(fields),
    )
