"""Versioned methods; evidence attaches to a component, never the whole app."""

from __future__ import annotations

import math
from dataclasses import replace

from vbg_interpreter.models import Calculation, CalculationStatus

MMHG_PER_KPA = 7.500616827041697
PACO2_CONSERVATIVE_ERRORS = (-8.74, 9.20)
METHODS = {
    "usual_tissue_transit_direction_v1": {
        "evidence_tier": "CONDITIONAL_PHYSIOLOGY_MODEL",
        "description": (
            "Under usual tissue transit: pHa ≥ pHv and 0 < PaCO2 ≤ PvCO2; applicability unassessed."
        ),
        "sources": ["docs/EVIDENCE.md#conditional-physiology"],
    },
    "bmp_gas_hco3_difference_v1": {
        "evidence_tier": "DESCRIPTIVE_COMPARISON",
        "description": (
            "BMP HCO3 minus venous gas-basis HCO3; absolute difference >10 mmol/L "
            "is a warning heuristic."
        ),
        "sources": ["docs/EVIDENCE.md#serum-chemistry"],
    },
    "fixed_ph_offset_v1": {
        "evidence_tier": "OWNER_SELECTED_HEURISTIC",
        "description": "Estimated arterial pH = measured venous pH + 0.04; rough fixed correction.",
        "sources": ["docs/EVIDENCE.md#arterial-estimates-and-provisional-interpretation"],
    },
    "fixed_paco2_offset_v1": {
        "evidence_tier": "OWNER_SELECTED_HEURISTIC",
        "description": "Estimated PaCO2 = measured PvCO2(mmHg) − 5; rough fixed correction.",
        "sources": ["docs/EVIDENCE.md#arterial-estimates-and-provisional-interpretation"],
    },
    "modeled_arterial_hh_v1": {
        "evidence_tier": "DERIVED_FROM_ESTIMATES",
        "description": (
            "Modeled arterial HCO3 = 0.0307 × estimated PaCO2 × 10^(estimated pH − 6.095)."
        ),
        "sources": ["docs/EVIDENCE.md#arterial-estimates-and-provisional-interpretation"],
    },
    "boston_estimated_gas_v1": {
        "evidence_tier": "IMPLEMENTED_SOFTWARE_RULESET",
        "description": (
            "Provisional Boston compensation assessment of the estimated "
            "arterial gas; chronicity unestablished."
        ),
        "sources": [
            "https://github.com/reblocke/stewart-light/tree/f277cac54801d85366cbadbf11804f6643f6a869"
        ],
    },
    "henderson_hasselbalch_v1": {
        "evidence_tier": "DERIVED_CALCULATION",
        "description": "Venous gas completion: HCO3 = 0.0307 × PvCO2 × 10^(pH − 6.095).",
        "sources": ["docs/EVIDENCE.md#venous-gas-and-standard-base-excess"],
    },
    "venous_sbe_van_slyke_37c_v1": {
        "evidence_tier": "DERIVED_CALCULATION",
        "description": "Venous SBE = 0.9287 × [HCO3 − 24.4 + 14.83 × (pH − 7.4)]; 37°C assumed.",
        "sources": ["https://doi.org/10.1097/00003246-199807000-00015"],
    },
    "reported_venous_sbe_v1": {
        "evidence_tier": "MEASURED_OR_REPORTED",
        "description": "Reported venous standard base excess; analyzer method unspecified.",
        "sources": [],
    },
    "farkas_simplified_93_v1": {
        "evidence_tier": "EXTERNALLY_EVALUATED",
        "description": "Estimated PaCO2 = measured PvCO2 − 0.22 × (93 − same-sample saturation%).",
        "sources": ["https://doi.org/10.1186/s40635-023-00564-w"],
    },
    "serum_anion_gap_v1": {
        "evidence_tier": "DERIVED_CALCULATION",
        "description": "Na − Cl − serum total CO2.",
        "sources": ["docs/EVIDENCE.md#serum-chemistry"],
    },
    "albumin_corrected_anion_gap_v1": {
        "evidence_tier": "DERIVED_CALCULATION",
        "description": "AG + 0.25 × (40 − albumin g/L).",
        "sources": ["docs/EVIDENCE.md#serum-chemistry"],
    },
    "sodium_chloride_difference_v1": {
        "evidence_tier": "DERIVED_CALCULATION",
        "description": "Na − Cl; descriptive strong-ion surrogate.",
        "sources": ["docs/EVIDENCE.md#serum-chemistry"],
    },
    "stewartlight_venous_partition_v1": {
        "evidence_tier": "IMPLEMENTED_SOFTWARE_RULESET",
        "description": "Venous-basis partition through the pinned structured Stewart Light helper.",
        "sources": [
            "https://github.com/reblocke/stewart-light/tree/f277cac54801d85366cbadbf11804f6643f6a869"
        ],
    },
}


def calculation(
    method: str,
    *,
    values: dict[str, float | str] | None = None,
    units: dict[str, str] | None = None,
    origins: dict[str, str] | None = None,
    provenance: str = "DERIVED_CALCULATION",
    missing: tuple[str, ...] = (),
    outside: tuple[str, ...] = (),
    limitations: tuple[str, ...] = (),
    domain_refusal: bool = False,
    applicability: str | None = None,
) -> Calculation:
    """Build the shared envelope, keeping numerical failure local to a calculation."""
    result_values = values or {}
    nonfinite = any(
        isinstance(v, (int, float)) and not math.isfinite(v) for v in result_values.values()
    )
    status = CalculationStatus.AVAILABLE
    if outside:
        status = CalculationStatus.UNAVAILABLE_OUTSIDE_SCOPE
    elif missing:
        status = CalculationStatus.UNAVAILABLE_MISSING_INPUT
    elif domain_refusal or nonfinite:
        status = CalculationStatus.MODEL_DOMAIN_REFUSAL
        limitations += (
            "Calculation is outside its finite numerical domain; no value was imputed.",
        )
    return Calculation(
        status=status,
        values=result_values if status is CalculationStatus.AVAILABLE else {},
        units=units or {},
        input_origins=origins or {},
        output_provenance=provenance,
        method_id=method,
        evidence_tier=str(METHODS[method]["evidence_tier"]),
        limitations=tuple(dict.fromkeys((*outside, *limitations))),
        missing_inputs=missing,
        applicability=applicability,
    )


def dependency_failure(*dependencies):
    """Select a typed dependency failure before any value dereference."""
    for status in (
        CalculationStatus.UNAVAILABLE_UNRELIABLE_INPUT,
        CalculationStatus.UNAVAILABLE_OUTSIDE_SCOPE,
        CalculationStatus.MODEL_DOMAIN_REFUSAL,
        CalculationStatus.UNAVAILABLE_MISSING_INPUT,
    ):
        for dependency in dependencies:
            if dependency.status is status:
                return dependency
    return None


def propagate_failure(result: Calculation, dependency) -> Calculation:
    return replace(
        result,
        status=dependency.status,
        values={},
        missing_inputs=dependency.missing_inputs,
        limitations=tuple(dict.fromkeys((*result.limitations, *dependency.limitations))),
    )
