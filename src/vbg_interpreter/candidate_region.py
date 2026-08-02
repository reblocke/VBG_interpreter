"""Farkas candidate-arterial-region calculation with fail-closed applicability."""

from __future__ import annotations

import math

from vbg_interpreter.evidence import (
    FARKAS_PACO2_COEFFICIENT_MMHG_PER_PERCENTAGE_POINT,
    FARKAS_PH_COEFFICIENT_PER_PERCENTAGE_POINT,
    FARKAS_PH_UNCERTAINTY_LABEL,
    FARKAS_PH_UNCERTAINTY_LOWER_OFFSET,
    FARKAS_PH_UNCERTAINTY_PROFILE_ID,
    FARKAS_PH_UNCERTAINTY_UPPER_OFFSET,
    FARKAS_SATURATION_REFERENCE_PERCENT,
    PACO2_ERROR_CONVENTION,
    PACO2_EVIDENCE,
    PACO2_INTERVAL_LABEL,
    PH_EVIDENCE,
    paco2_profile_for_oxygen,
)
from vbg_interpreter.models import (
    CandidateArterialPoint,
    CandidateArterialRegion,
    CandidateRegionReasonCode,
    CandidateRegionStatus,
    CandidateRegionWarningCode,
    DrawSite,
    EvidenceTier,
    LimitationCode,
    NormalizedExplorerInput,
    NumericInterval,
    SpecimenType,
    TriState,
    VbgExplorerRequest,
)
from vbg_interpreter.normalize import normalize_request


def calculate_candidate_arterial_region(
    request: VbgExplorerRequest,
    *,
    normalized_input: NormalizedExplorerInput | None = None,
) -> CandidateArterialRegion:
    """Return the Farkas pH/PaCO2 sensitivity region when its scope is explicit.

    This function deliberately returns ``UNAVAILABLE`` for incomplete context rather
    than refusing observed VBG or chemistry interpretation elsewhere in the product.
    """

    normalized = normalized_input if normalized_input is not None else normalize_request(request)
    if not isinstance(normalized, NormalizedExplorerInput):
        raise TypeError("normalized_input must be NormalizedExplorerInput.")
    reasons = _gate_reasons(normalized)
    if reasons:
        return CandidateArterialRegion(
            status=CandidateRegionStatus.UNAVAILABLE,
            reason_codes=tuple(reasons),
        )

    vbg = normalized.current_vbg
    saturation = vbg.venous_o2_saturation
    if saturation is None:  # pragma: no cover - guarded by _gate_reasons
        raise AssertionError("Eligible candidate region requires saturation.")
    profile = paco2_profile_for_oxygen(normalized.context.supplemental_oxygen)
    delta = FARKAS_SATURATION_REFERENCE_PERCENT - saturation.normalized_percentage_points
    estimated_ph = vbg.ph + FARKAS_PH_COEFFICIENT_PER_PERCENTAGE_POINT * delta
    estimated_paco2 = vbg.pco2_mmhg + FARKAS_PACO2_COEFFICIENT_MMHG_PER_PERCENTAGE_POINT * delta
    ph_lower = estimated_ph + FARKAS_PH_UNCERTAINTY_LOWER_OFFSET
    ph_upper = estimated_ph + FARKAS_PH_UNCERTAINTY_UPPER_OFFSET
    paco2_lower = estimated_paco2 - profile.error_loa_upper_mmhg
    paco2_upper = estimated_paco2 - profile.error_loa_lower_mmhg
    domain_failure = _domain_failure(
        estimated_ph=estimated_ph,
        estimated_paco2=estimated_paco2,
        ph_lower=ph_lower,
        ph_upper=ph_upper,
        paco2_lower=paco2_lower,
        paco2_upper=paco2_upper,
    )
    if domain_failure is not None:
        return CandidateArterialRegion(
            status=CandidateRegionStatus.MODEL_DOMAIN_REFUSAL,
            reason_codes=(domain_failure,),
        )
    warnings = (
        (CandidateRegionWarningCode.SATURATION_ABOVE_SIMPLIFIED_REFERENCE,)
        if saturation.normalized_percentage_points > FARKAS_SATURATION_REFERENCE_PERCENT
        else ()
    )
    return CandidateArterialRegion(
        status=CandidateRegionStatus.AVAILABLE,
        point=CandidateArterialPoint(ph=estimated_ph, paco2_mmhg=estimated_paco2),
        ph_interval=NumericInterval(
            lower=ph_lower,
            upper=ph_upper,
            profile_id=FARKAS_PH_UNCERTAINTY_PROFILE_ID,
            label=FARKAS_PH_UNCERTAINTY_LABEL,
            evidence_tier=EvidenceTier.DERIVATION_ONLY,
        ),
        paco2_interval=NumericInterval(
            lower=paco2_lower,
            upper=paco2_upper,
            profile_id=profile.profile_id,
            label=PACO2_INTERVAL_LABEL,
            evidence_tier=EvidenceTier.EXTERNALLY_EVALUATED,
            error_convention=PACO2_ERROR_CONVENTION,
        ),
        ph_evidence=PH_EVIDENCE,
        paco2_evidence=PACO2_EVIDENCE,
        uncertainty_profile_id=profile.profile_id,
        warning_codes=warnings,
        limitation_codes=(LimitationCode.SOURCE_SPECTRUM_NOT_ESTABLISHED,),
    )


def candidate_region_information_needs(
    region: CandidateArterialRegion,
) -> tuple[CandidateRegionReasonCode, ...]:
    """Expose the exact typed blockers for a caller-owned information-gain list."""

    if not isinstance(region, CandidateArterialRegion):
        raise TypeError("region must be CandidateArterialRegion.")
    return region.reason_codes


def _gate_reasons(value: NormalizedExplorerInput) -> list[CandidateRegionReasonCode]:
    vbg = value.current_vbg
    context = value.context
    reasons: list[CandidateRegionReasonCode] = []
    if vbg.specimen_type is SpecimenType.UNKNOWN:
        reasons.append(CandidateRegionReasonCode.SPECIMEN_TYPE_UNKNOWN)
    elif vbg.specimen_type is not SpecimenType.PERIPHERAL_VENOUS:
        reasons.append(CandidateRegionReasonCode.SPECIMEN_OUTSIDE_PERIPHERAL_VENOUS_SCOPE)
    if vbg.draw_site is DrawSite.UNKNOWN:
        reasons.append(CandidateRegionReasonCode.DRAW_SITE_UNKNOWN)
    elif vbg.draw_site is not DrawSite.UPPER_EXTREMITY_PERIPHERAL:
        reasons.append(CandidateRegionReasonCode.DRAW_SITE_OUTSIDE_UPPER_EXTREMITY_SCOPE)
    if vbg.venous_o2_saturation is None:
        reasons.append(CandidateRegionReasonCode.MISSING_SAME_SAMPLE_VENOUS_SATURATION)
    if context.known_poor_perfusion_or_hemodynamic_instability is TriState.UNKNOWN:
        reasons.append(CandidateRegionReasonCode.PERFUSION_OR_HEMODYNAMIC_STATUS_UNKNOWN)
    elif context.known_poor_perfusion_or_hemodynamic_instability is TriState.YES:
        reasons.append(CandidateRegionReasonCode.KNOWN_POOR_PERFUSION_OR_HEMODYNAMIC_INSTABILITY)
    if context.recent_major_ventilation_or_treatment_change is TriState.UNKNOWN:
        reasons.append(CandidateRegionReasonCode.RECENT_VENTILATION_OR_TREATMENT_CHANGE_UNKNOWN)
    elif context.recent_major_ventilation_or_treatment_change is TriState.YES:
        reasons.append(CandidateRegionReasonCode.RECENT_VENTILATION_OR_TREATMENT_CHANGE)
    if context.material_preanalytic_concern is TriState.UNKNOWN:
        reasons.append(CandidateRegionReasonCode.PREANALYTIC_STATUS_UNKNOWN)
    elif context.material_preanalytic_concern is TriState.YES:
        reasons.append(CandidateRegionReasonCode.MATERIAL_PREANALYTIC_CONCERN)
    return reasons


def _domain_failure(
    *,
    estimated_ph: float,
    estimated_paco2: float,
    ph_lower: float,
    ph_upper: float,
    paco2_lower: float,
    paco2_upper: float,
) -> CandidateRegionReasonCode | None:
    values = (estimated_ph, estimated_paco2, ph_lower, ph_upper, paco2_lower, paco2_upper)
    if not all(math.isfinite(value) for value in values):
        return CandidateRegionReasonCode.NONFINITE_MODEL_OUTPUT
    if estimated_ph <= 0:
        return CandidateRegionReasonCode.NONPOSITIVE_ESTIMATED_PH
    if estimated_paco2 <= 0:
        return CandidateRegionReasonCode.NONPOSITIVE_ESTIMATED_PACO2
    if ph_lower <= 0 or ph_upper <= 0:
        return CandidateRegionReasonCode.NONPOSITIVE_PH_INTERVAL_ENDPOINT
    if paco2_lower <= 0 or paco2_upper <= 0:
        return CandidateRegionReasonCode.NONPOSITIVE_PACO2_INTERVAL_ENDPOINT
    if ph_lower > ph_upper or paco2_lower > paco2_upper:
        return CandidateRegionReasonCode.INVALID_INTERVAL_ORDER
    return None
