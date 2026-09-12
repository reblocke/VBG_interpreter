"""Warning-only input sanity policy; finite arithmetic is retained separately."""

import math

from vbg_interpreter.models import VbgExplorerRequest
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
    observations = []
    for field, value in values.items():
        low, high, label = LIMITS[field]
        if value is not None and not low <= value <= high:
            observations.append(
                {
                    "policy_id": POLICY_ID,
                    "field": field,
                    "severity": "WARNING",
                    "limits": [low, high],
                    "value": value if math.isfinite(value) else None,
                    "suppresses_axis_interpretation": field in ("ph", "pco2"),
                    "message": f"{label} is outside the input sanity interval {low:g}–{high:g}. "
                    "Check the entered value and unit; the input has not been corrected. "
                    + (
                        "This coordinate is not used for physiology interpretation or shading."
                        if field in ("ph", "pco2")
                        else "Independent gas interpretation remains available."
                    ),
                }
            )
    return tuple(observations)


def unreliable_axes(observations: tuple[dict[str, object], ...]) -> set[str]:
    return {str(o["field"]) for o in observations if o["suppresses_axis_interpretation"]}
