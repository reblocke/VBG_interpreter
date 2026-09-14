"""Warning-only input sanity policy; finite arithmetic is retained separately."""

import math
from dataclasses import replace

from vbg_interpreter.models import CalculationStatus, VbgExplorerRequest
from vbg_interpreter.normalize import normalize_pco2_to_mmhg

POLICY_ID = "input_sanity_v1"
LIMITS = {
    "ph": (6.0, 8.5, "pH"),
    "pco2": (5.0, 250.0, "PvCO2 (mmHg)"),
    "hco3": (1.0, 100.0, "Blood gas HCO3 (mmol/L)"),
    "bmp_hco3": (1.0, 100.0, "BMP HCO3 (mmol/L)"),
    "sodium": (80.0, 220.0, "Sodium (mmol/L)"),
    "chloride": (40.0, 200.0, "Chloride (mmol/L)"),
    "albumin": (0.0, 80.0, "Albumin (g/L)"),
    "lactate": (0.0, 40.0, "Lactate (mmol/L)"),
    "base_excess": (-60.0, 60.0, "Reported base excess (mmol/L)"),
}


def input_observations(request: VbgExplorerRequest) -> tuple[dict[str, object], ...]:
    source, chem = request.current_vbg, request.current_chemistry
    pco2 = None
    if source.pco2 is not None:
        try:
            pco2 = normalize_pco2_to_mmhg(source.pco2, source.pco2_unit)
        except ValueError:
            pco2 = math.inf
    values = dict(
        ph=source.ph,
        pco2=pco2,
        hco3=source.hco3_mmol_l,
        bmp_hco3=chem.serum_total_co2_mmol_l,
        sodium=chem.sodium_mmol_l,
        chloride=chem.chloride_mmol_l,
        albumin=chem.albumin_g_l,
        lactate=chem.lactate_mmol_l,
        base_excess=source.base_excess_mmol_l,
    )
    if chem.albumin is not None and chem.albumin_g_l is None:
        values["albumin"] = math.inf
    return tuple(
        observation
        for field, value in values.items()
        if (observation := sanity_observation(field, value, "SUPPLIED", (field,)))
    )


def sanity_observation(field, value, origin, source_fields):
    low, high, label = LIMITS[field]
    if value is None or low <= value <= high:
        return None
    prefix = "HH-reconstructed " if origin == "HH_RECONSTRUCTED" else "Supplied "
    return {
        "policy_id": POLICY_ID,
        "field": field,
        "origin": origin,
        "source_field_ids": tuple(source_fields),
        "severity": "WARNING",
        "limits": [low, high],
        "value": value if math.isfinite(value) else None,
        "suppresses_axis_interpretation": origin == "SUPPLIED" and field in ("ph", "pco2"),
        "message": prefix + f"{label} is outside the software sanity interval {low:g}–{high:g}. "
        "Check its source values and units; finite arithmetic is retained. "
        "Only interpretations and estimated paired plots that depend on this value are withheld.",
    }


def gas_observations(request, gas):
    observations = list(input_observations(request))
    for axis, calc in gas.calculated_values.items():
        if calc.status is CalculationStatus.AVAILABLE:
            observation = sanity_observation(
                axis,
                calc.values[axis],
                "HH_RECONSTRUCTED",
                tuple(k for k in calc.input_origins if k in LIMITS),
            )
            if observation:
                observations.append(observation)
    # The HH comparator is also consumed by SBE with a redundant supplied bicarbonate.
    if gas.consistency.status is CalculationStatus.AVAILABLE:
        observation = sanity_observation(
            "hco3", gas.consistency.values["hh_hco3"], "HH_RECONSTRUCTED", ("ph", "pco2")
        )
        if observation:
            observations.append(observation)
    return tuple(observations)


def component_warnings(observations, axis, selection):
    return tuple(
        o
        for o in observations
        if (o["origin"] == "SUPPLIED" and o["field"] in selection.source_field_ids)
        or (
            o["origin"] == "HH_RECONSTRUCTED"
            and o["field"] == axis
            and selection.source_coordinate_origin == "HH_RECONSTRUCTED"
        )
    )


def qualify_calculation(calc, observations, *, output_axis=None):
    """Qualify finite arithmetic using its existing operand provenance, without changing status."""
    aliases = {"serum total CO2": "bmp_hco3", "measured venous pH": "ph"}
    dependencies = set()
    for key, origin in calc.input_origins.items():
        key = aliases.get(key.removeprefix("sbe."), key.removeprefix("sbe."))
        if key in LIMITS:
            dependencies.add(
                (
                    key,
                    "HH_RECONSTRUCTED"
                    if origin == "CALCULATED_HENDERSON_HASSELBALCH"
                    else "SUPPLIED",
                )
            )
    if calc.method_id == "bmp_gas_hco3_difference_v1":
        if calc.input_origins.get("gas_basis") == "HH_FROM_MEASURED_PH_PVCO2":
            dependencies.update(
                (("ph", "SUPPLIED"), ("pco2", "SUPPLIED"), ("hco3", "HH_RECONSTRUCTED"))
            )
        elif calc.input_origins.get("gas_basis") == "SUPPLIED_BLOOD_GAS_HCO3":
            dependencies.add(("hco3", "SUPPLIED"))
    if output_axis:
        dependencies.add((output_axis, "HH_RECONSTRUCTED"))
    warnings = tuple(o for o in observations if (o["field"], o["origin"]) in dependencies)
    return replace(calc, input_warnings=warnings)


def unreliable_axes(observations: tuple[dict[str, object], ...]) -> set[str]:
    return {str(o["field"]) for o in observations if o["suppresses_axis_interpretation"]}
