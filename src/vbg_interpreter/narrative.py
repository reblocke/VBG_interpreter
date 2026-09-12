"""Deterministic summary assembled from the same structured results as the detail views."""

from vbg_interpreter.models import CalculationStatus
from vbg_interpreter.physiology import _boundary_display


def build_narrative(request, ph, co2, provisional, sensitivity, direction, comparison):
    source = request.current_vbg
    parts = []
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
    if flagged:
        parts.insert(
            0,
            "Measured " + "/".join(flagged) + " has an input sanity warning. "
            "Available measurements and finite arithmetic remain below; "
            "full gas interpretation is withheld.",
        )
    elif parts:
        parts[0] = "The best-guess conversion shows " + parts[0][:1].lower() + parts[0][1:]
    else:
        parts.append(
            "Available measured and calculated values are shown below; "
            "no arterial estimate is available."
        )
    if source.venous_o2_saturation is not None and co2.method_id != "farkas_simplified_93_v1":
        parts.append(
            "The supplied saturation was not used because the sample is not explicitly peripheral."
        )
    if provisional.status is CalculationStatus.AVAILABLE:
        parts.append(
            "Provisional gas-only interpretation: "
            + provisional.assessment["primary_process_guess"]
            + "."
        )
        parts.append(
            (
                provisional.assessment["modeled_vs_expected"][:1].upper()
                + provisional.assessment["modeled_vs_expected"][1:]
            ).rstrip(".")
            + "."
        )
    else:
        parts.append(
            "A complete provisional gas-only interpretation is unavailable: "
            + provisional.status.value.lower().replace("_", " ")
            + "."
        )
    parts.extend(
        [
            sensitivity["summary"],
            "Applicability is unassessed; clinical context and pH uncertainty remain unresolved.",
        ]
    )
    disagreement = []
    bound = direction["axes"]["pco2"]["bound"]
    if bound is not None and co2.status is CalculationStatus.AVAILABLE:
        if co2.values["point"] > bound:
            disagreement.append(
                "The Farkas point lies above the conditional venous CO2 upper direction."
            )
        if "upper" in co2.values and co2.values["upper"] > bound:
            disagreement.append(
                "The CO2 agreement range extends outside the conditional physiology shading."
            )
    if disagreement:
        parts.extend(disagreement)
        parts.append(
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
    parts.append(chemistry_note)
    return {
        "best_guess": " ".join(parts),
        "conditional_physiology": direction["assumption"] + " " + direction["summary"],
        "model_disagreements": disagreement,
    }
