"""Conditional measured-source direction metadata shared by narrative and SVG."""

from vbg_interpreter.models import CalculationStatus, SampleType, VbgExplorerRequest
from vbg_interpreter.normalize import normalize_pco2_to_mmhg
from vbg_interpreter.observations import unreliable_axes

MODEL_ID = "usual_tissue_transit_direction_v1"
CAPTION = (
    "Conditional arterial direction under usual tissue transit; "
    "not a confidence region or guaranteed ABG bound."
)
ASSUMPTION = (
    "Based on physiology, assuming usual steady-state tissue transit with net CO2 addition "
    "and acidification, "
    "arterial pH is at least venous pH and arterial CO2 is no greater than venous CO2. "
    "Sampling, local metabolism, perfusion and nonsteady state can invalidate this model."
)


def direction_metadata(request: VbgExplorerRequest, observations: tuple) -> dict[str, object]:
    source = request.current_vbg
    blocked = unreliable_axes(observations)
    axes = {}
    for field, raw in (("ph", source.ph), ("pco2", source.pco2)):
        status = (
            CalculationStatus.UNAVAILABLE_MISSING_INPUT
            if raw is None
            else CalculationStatus.UNAVAILABLE_UNRELIABLE_INPUT
            if field in blocked
            else CalculationStatus.AVAILABLE
        )
        axis = {"status": status.value, "bound": None, "possibilities": []}
        if status is CalculationStatus.AVAILABLE:
            value = raw if field == "ph" else normalize_pco2_to_mmhg(raw, source.pco2_unit)
            axis["bound"] = value
            axis["relation"] = ">=" if field == "ph" else "0 < arterial CO2 <="
            if field == "ph":
                axis["possibilities"] = (
                    (["acidemia"] if value < 7.35 else [])
                    + (["near-normal pH"] if value <= 7.45 else [])
                    + ["alkalemia"]
                )
                axis["display_bound"] = _boundary_display(value, (7.35, 7.45), 2)
            else:
                axis["possibilities"] = ["below 40 mmHg"]
                if value >= 40:
                    axis["possibilities"].append("equal to 40 mmHg")
                if value > 40:
                    axis["possibilities"].append("above 40 mmHg")
                axis["display_bound"] = _boundary_display(value, (40,), 1)
        axes[field] = axis
    usable = [a for a in axes.values() if a["status"] == CalculationStatus.AVAILABLE]
    status = (
        CalculationStatus.AVAILABLE
        if usable
        else CalculationStatus.UNAVAILABLE_UNRELIABLE_INPUT
        if blocked
        else CalculationStatus.UNAVAILABLE_MISSING_INPUT
    )
    caption = CAPTION
    assumption = ASSUMPTION
    if source.sample_type is SampleType.UNKNOWN:
        caption += " Sample type not specified."
        assumption = (
            "Sample type unknown; an illustrative systemic-venous assumption is used. " + assumption
        )
    if source.sample_type is not SampleType.UNKNOWN:
        caption += f" Sample: {source.sample_type.value.lower()}."
    parts = []
    ph, co2 = axes["ph"], axes["pco2"]
    if ph["bound"] is not None:
        parts.append(
            f"Conditional arterial pH ≥ {ph['display_bound']}: "
            + ", ".join(ph["possibilities"])
            + (" remains possible" if len(ph["possibilities"]) == 1 else " remain possible")
            + "; no upper pH bound is identified."
        )
    if co2["bound"] is not None:
        parts.append(
            f"Conditional 0 < PaCO2 ≤ {co2['display_bound']} mmHg: "
            + ", ".join(co2["possibilities"])
            + (" remains possible" if len(co2["possibilities"]) == 1 else " remain possible")
            + " relative to the plotting reference. No positive minimum CO2 is identified."
        )
    for field, label in (("ph", "pH"), ("pco2", "CO2")):
        if axes[field]["bound"] is None:
            reason = "flagged input" if field in blocked else "missing measured coordinate"
            parts.append(f"No {label} direction is shown because of a {reason}.")
    return {
        "model_id": MODEL_ID,
        "status": status.value,
        "sample_type": source.sample_type.value,
        "axes": axes,
        "assumption": assumption,
        "caption": caption,
        "summary": " ".join(parts)
        + " These are coordinate possibilities, not exclusions of metabolic or respiratory "
        "components, mixed disorders, or chronicity.",
        "limitations": [
            "Unshaded space is not clinically ruled out.",
            "The reference cross is not a diagnostic boundary.",
            "Marginal directions do not establish joint attainability or likelihood. "
            "Non-acidemic pH does not exclude metabolic acidosis; CO2 below 40 does not "
            "exclude relative respiratory acidosis.",
        ],
    }


def _boundary_display(value: float, boundaries: tuple, places: int) -> str:
    rounded = round(value, places)
    if rounded in boundaries and value != rounded:
        return f"{value:.8g} (classification uses full precision)"
    return f"{value:.{places}f}"
