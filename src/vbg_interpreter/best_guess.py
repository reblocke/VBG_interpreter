"""Provisional gas-only assessment; no invented chemistry, BE or chronicity input."""

import math
from dataclasses import dataclass, replace

from stewartlight.interpret import assess_boston

from vbg_interpreter.evidence import calculation, dependency_failure, propagate_failure
from vbg_interpreter.models import Calculation, CalculationStatus, ProvisionalInterpretation
from vbg_interpreter.serialization import to_primitive
from vbg_interpreter.venous_gas import hco3_from_ph_pco2


@dataclass(frozen=True)
class _EstimatedGas:
    """Structural adapter for the four attributes read by the pinned Boston helper.

    No AcidBaseInput is constructed: its required chemistry and SBE do not apply here.
    False disables the upstream chronic-only branch; it does not assert an acute process.
    """

    ph: float
    pco2_mmhg: float
    hco3_mmol_l: float
    suspect_chronic_hypercapnia: bool = False


def modeled_hco3(ph: Calculation, co2: Calculation) -> Calculation:
    kwargs = dict(
        origins={"ph": ph.output_provenance, "pco2": co2.output_provenance},
        provenance="CALCULATED_FROM_ARTERIAL_ESTIMATES",
        limitations=(
            (
                "Modeled arterial bicarbonate from the estimated pair; not measured "
                "or venous bicarbonate."
            ),
        ),
    )
    failure = dependency_failure(ph, co2)
    if failure is not None:
        return propagate_failure(calculation("modeled_arterial_hh_v1", **kwargs), failure)
    try:
        value = hco3_from_ph_pco2(ph=ph.values["ph"], pco2_mmhg=co2.values["point"])
        kwargs["domain_refusal"] = value <= 0
        return calculation(
            "modeled_arterial_hh_v1",
            values={"modeled_hco3": value},
            units={"modeled_hco3": "mmol/L"},
            **kwargs,
        )
    except (ArithmeticError, ValueError):
        kwargs["domain_refusal"] = True
        return calculation("modeled_arterial_hh_v1", **kwargs)


# Exact primary labels and fixed comparison templates from the pinned Boston helper.
# Unknown upstream text refuses this adapter rather than silently changing scientific meaning.
PRIMARY_LABELS = {
    **{
        f"{p} likely": f"{p} suggested by this estimate"
        for p in (
            "metabolic acidosis",
            "metabolic alkalosis",
            "respiratory acidosis",
            "respiratory alkalosis",
        )
    },
    **{
        p: p
        for p in (
            "acidemia with unclear dominant process",
            "alkalemia with unclear dominant process",
            "near-normal pH with compensated respiratory acidosis or mixed process possible",
            "near-normal pH with compensated respiratory alkalosis or mixed process possible",
            "near-normal pH with compensated or mixed process possible",
            "no clear primary process by simple Boston heuristics",
        )
    },
}
COMPARISON_TEMPLATES = {
    (
        "measured PaCO2 is above the Winter's formula range, suggesting "
        "superimposed respiratory acidosis"
    ): "ABOVE",
    (
        "measured PaCO2 is below the Winter's formula range, suggesting "
        "superimposed respiratory alkalosis"
    ): "BELOW",
    (
        "measured PaCO2 is above the expected range, which may reflect "
        "superimposed respiratory acidosis or limited ventilatory reserve"
    ): "ABOVE",
    (
        "measured PaCO2 is below the expected range, suggesting superimposed respiratory alkalosis"
    ): "BELOW",
    "measured PaCO2 is within the expected range": "WITHIN",
    "measured HCO3 is within the broad acute/chronic expected range": "WITHIN",
    **{
        (
            f"measured HCO3 is {direction} than expected for acute/chronic {process}, "
            f"suggesting an additional {additional}"
        ): category
        for direction, additional, category in (
            ("lower", "metabolic acidosis", "BELOW"),
            ("higher", "metabolic alkalosis", "ABOVE"),
        )
        for process in ("respiratory acidosis", "respiratory alkalosis")
    },
    "Near-normal pH does not exclude compensated or mixed acid-base processes.": "NOT_APPLIED",
}


def _adapt_assessment(raw: dict) -> dict:
    primary = raw["primary_process_guess"]
    if primary not in PRIMARY_LABELS:
        raise ValueError("Unknown pinned Boston primary label")
    comparison = raw.pop("measured_vs_expected")
    template = comparison.split(" (", 1)[0]
    if template not in COMPARISON_TEMPLATES:
        raise ValueError("Unknown pinned Boston comparison template")
    expected = raw["expected_compensation"]
    if any(isinstance(v, float) and not math.isfinite(v) for v in expected.values()):
        raise ValueError("Nonfinite compensation result")
    raw["primary_category"] = primary
    raw["compensation_category"] = COMPARISON_TEMPLATES[template]
    # Display labels come only from the whitelisted pinned template, not arbitrary prose.
    detail = template.partition(", suggesting ")[2] or template.partition(", which may reflect ")[2]
    raw["scenario_example"] = COMPARISON_TEMPLATES[template].lower().replace("_", " ")
    if detail:
        raw["scenario_example"] += " — " + detail
    raw["primary_process_guess"] = PRIMARY_LABELS[primary]
    # Only the known comparison template's leading source attribution is adapted.
    raw["modeled_vs_expected"] = (
        "modeled" + comparison[len("measured") :]
        if template.startswith("measured ")
        else comparison
    )
    return raw


def assess_estimated_gas(
    ph: Calculation, co2: Calculation, hco3: Calculation
) -> ProvisionalInterpretation:
    limits = (
        "Provisional interpretation of estimated coordinates; other "
        "acid–base processes are not excluded.",
        "A single gas does not establish chronicity; acute and chronic "
        "comparisons are contextual only.",
    )
    failure = dependency_failure(ph, co2, hco3)
    if failure is not None:
        return ProvisionalInterpretation(
            failure.status,
            missing_inputs=failure.missing_inputs,
            limitations=(*limits, *failure.limitations),
        )
    try:
        gas = _EstimatedGas(ph.values["ph"], co2.values["point"], hco3.values["modeled_hco3"])
        # The pinned helper is duck-typed; tests compare this adapter with its full input.
        assessment = _adapt_assessment(to_primitive(assess_boston(gas)))
        return ProvisionalInterpretation(
            CalculationStatus.AVAILABLE, assessment=assessment, limitations=limits
        )
    except (ArithmeticError, ValueError):
        return ProvisionalInterpretation(CalculationStatus.MODEL_DOMAIN_REFUSAL, limitations=limits)


def interpretation_sensitivity(
    ph: Calculation, co2: Calculation, provisional: ProvisionalInterpretation
) -> dict:
    if provisional.status is not CalculationStatus.AVAILABLE:
        return {
            "status": provisional.status.value,
            "scenarios": [],
            "summary": "Gas-only sensitivity is unavailable from the usable estimated pair.",
        }
    if co2.method_id != "farkas_simplified_93_v1":
        return {
            "status": "NOT_QUANTIFIED",
            "scenarios": [],
            "summary": (
                "Robustness is not quantified: fixed corrections have no sourced "
                "individual uncertainty interval."
            ),
        }
    scenarios = []
    for name, key in (("lower", "lower"), ("point", "point"), ("upper", "upper")):
        scenario_co2 = replace(co2, values={**co2.values, "point": co2.values[key]})
        hco3 = modeled_hco3(ph, scenario_co2)
        assessment = assess_estimated_gas(ph, scenario_co2, hco3)
        scenarios.append(
            {
                "name": name,
                "ph": ph.values["ph"],
                "pco2": co2.values[key],
                "hco3": hco3.values.get("modeled_hco3"),
                "status": assessment.status.value,
                "assessment": assessment.assessment,
            }
        )
    if any(s["status"] != CalculationStatus.AVAILABLE for s in scenarios):
        status, summary = (
            "INCOMPLETE",
            "CO2 scenario sensitivity is incomplete; no robustness claim is made.",
        )
    else:
        signatures = {
            (s["assessment"]["primary_category"], s["assessment"]["compensation_category"])
            for s in scenarios
        }
        status = "CHANGES" if len(signatures) > 1 else "NO_CHANGE_TESTED"
        summary = (
            (
                "The provisional interpretation changes across the tested CO2 "
                "scenarios; the point estimate is not robust to this CO2 variation."
            )
            if len(signatures) > 1
            else (
                "No change in the tested CO₂ scenarios; pH uncertainty and full "
                "robustness remain unassessed."
            )
        )
    if status == "CHANGES":
        examples = list(dict.fromkeys(s["assessment"]["scenario_example"] for s in scenarios))
        summary += " Tested compensation examples: " + "; ".join(examples) + "."
        primary = list(dict.fromkeys(s["assessment"]["primary_process_guess"] for s in scenarios))
        if len(primary) > 1:
            summary += " Tested primary-process examples: " + "; ".join(primary) + "."
    return {
        "status": status,
        "scenarios": scenarios,
        "summary": summary,
        "limitations": [
            (
                "Lower, point and upper CO2 examples hold estimated pH fixed and "
                "recompute HH bicarbonate at each point."
            ),
            "These scenarios are not exhaustive and have no probability meaning.",
        ],
    }
