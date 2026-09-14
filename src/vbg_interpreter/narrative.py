"""Deterministic summary assembled from the same structured results as the detail views."""

from vbg_interpreter.models import CalculationStatus
from vbg_interpreter.physiology import _boundary_display


def build_narrative(request, ph, co2, provisional, sensitivity, direction, comparison):
    source = request.current_vbg
    parts = []
    details = []
    if ph.status is CalculationStatus.AVAILABLE:
        parts.append(
            f"Estimated arterial pH {_boundary_display(ph.values['ph'], (7.35, 7.45), 2)} "
            "(fixed +0.04)."
        )
    if co2.status is CalculationStatus.AVAILABLE:
        method = (
            "peripheral Farkas" if co2.method_id == "farkas_simplified_93_v1" else "fixed −5 mmHg"
        )
        parts.append(
            f"Estimated PaCO2 {co2.values['point']:.1f} mmHg "
            f"({method}; sample {source.sample_type.value.lower()})."
        )
    flagged = [
        {"ph": "venous pH", "pco2": "PvCO2"}[field]
        for field, axis in direction["axes"].items()
        if axis["status"] == CalculationStatus.UNAVAILABLE_UNRELIABLE_INPUT
    ]
    if not parts:
        parts.append(
            "Available measured and calculated values are shown below; "
            "no arterial estimate is available."
        )
    routes = list(
        dict.fromkeys(c.route_label for c in (ph, co2) if c.status is CalculationStatus.AVAILABLE)
    )
    parts.extend(route + "." for route in routes)
    for component in (ph, co2):
        for limitation in component.limitations:
            if limitation.startswith(
                (
                    "Best guess using",
                    "Farkas estimate assumes",
                    "Central sample:",
                    "Agreement interval is nonphysical",
                )
            ):
                details.append(limitation)
    if provisional.status is CalculationStatus.AVAILABLE:
        parts.append(
            "Provisional gas-only interpretation: "
            + provisional.assessment["primary_process_guess"]
            + "."
        )
        details.append(
            (
                provisional.assessment["modeled_vs_expected"][:1].upper()
                + provisional.assessment["modeled_vs_expected"][1:]
            ).rstrip(".")
            + "."
        )
    elif provisional.status is CalculationStatus.UNAVAILABLE_UNRELIABLE_INPUT:
        parts.append(
            "Provisional interpretation, sensitivity and the estimated paired plot are withheld "
            "because a required source or HH-reconstructed coordinate has a sanity warning. "
            "Finite arithmetic is retained."
        )
    else:
        parts.append("A complete provisional gas-only interpretation is unavailable.")
    short_sensitivity = {
        "CHANGES": (
            "The interpretation changes across tested CO2 scenarios; "
            "the point is not robust to this variation."
        ),
        "NO_CHANGE_TESTED": (
            "No change across tested CO2 scenarios; full robustness remains unassessed."
        ),
        "NOT_QUANTIFIED": "Robustness is not quantified for this input route.",
        "INCOMPLETE": "CO2 sensitivity is incomplete.",
    }.get(sensitivity["status"], "Gas-only sensitivity is unavailable.")
    if provisional.status is not CalculationStatus.UNAVAILABLE_UNRELIABLE_INPUT:
        parts.append(short_sensitivity)
    parts.append("Applicability is unassessed.")
    details.extend(
        [sensitivity["summary"], "Clinical context and pH uncertainty remain unresolved."]
    )
    disagreement = []
    bound = direction["axes"]["pco2"]["bound"]
    if bound is not None and co2.status is CalculationStatus.AVAILABLE:
        if co2.values["point"] > bound:
            disagreement.append(
                "The Farkas point lies above the conditional venous CO2 upper direction."
            )
        if co2.agreement.status == "AVAILABLE" and co2.agreement.upper > bound:
            disagreement.append(
                "The CO2 agreement range extends outside the conditional physiology shading."
            )
    if disagreement:
        details.extend(disagreement)
        details.append(
            "The empirical estimate and conditional physiology model differ; "
            "values and ranges are retained without clipping."
        )
    chemistry_note = "The gas-only interpretation does not reconcile serum chemistry."
    if comparison.status is CalculationStatus.AVAILABLE:
        v = comparison.values
        chemistry_note += (
            f" BMP HCO3 {v['bmp_hco3']:.1f} versus "
            f"gas-basis HCO3 {v['gas_basis_hco3']:.1f} mmol/L; "
            f"BMP minus gas {v['bmp_minus_gas_hco3']:+.1f} mmol/L; "
            f"timing {v['timing'].lower().replace('_', ' ')}."
        )
        if abs(v["bmp_minus_gas_hco3"]) > 10:
            chemistry_note += " Large discrepancy by the >10 mmol/L warning heuristic."
    details.append(chemistry_note)
    return {
        "best_guess": " ".join(parts),
        "conditional_physiology": (
            (
                "Sample type unknown; peripheral/systemic assumptions are unconfirmed. "
                if source.sample_type.value == "UNKNOWN"
                else ""
            )
            + (
                "A supplied gas coordinate has a sanity warning; "
                "only independent usable axes contribute. "
                if flagged
                else ""
            )
            + conditional_summary(direction)
        ),
        "details": details
        + [direction["assumption"], direction["summary"], *direction["limitations"]],
        "model_disagreements": disagreement,
    }


def conditional_summary(direction):
    coordinates = []
    ph, co2 = direction["axes"]["ph"], direction["axes"]["pco2"]
    if ph["bound"] is not None:
        coordinates.append("arterial pH ≥ " + ph["display_bound"])
    if co2["bound"] is not None:
        coordinates.append("0 < PaCO2 ≤ " + co2["display_bound"] + " mmHg")
    if not coordinates:
        return "No usable supplied gas coordinate supports a conditional direction."
    return (
        "Under usual steady-state tissue transit, "
        + "; ".join(coordinates)
        + ". These directions are not guaranteed bounds or probability regions; "
        "mixed processes and chronicity remain unresolved."
    )
