"""One public, progressive interpretation entry point for the VBG Explorer."""

from __future__ import annotations

from vbg_interpreter.candidate_region import calculate_candidate_arterial_region
from vbg_interpreter.chemistry import calculate_chemistry_interpretation
from vbg_interpreter.evidence import explorer_provenance
from vbg_interpreter.longitudinal import build_longitudinal_context
from vbg_interpreter.models import (
    CandidateArterialRegion,
    CandidateRegionReasonCode,
    CandidateRegionStatus,
    InformationNeedCode,
    LimitationCode,
    StateEnumerationStatus,
    VbgExplorerRequest,
    VbgExplorerResult,
)
from vbg_interpreter.normalize import normalize_request
from vbg_interpreter.state_space import enumerate_candidate_state_space


def interpret_vbg(request: VbgExplorerRequest) -> VbgExplorerResult:
    """Interpret one current VBG and chemistry panel without forcing a diagnosis.

    Every lane is computed independently where its requirements are met.  Missing
    model context therefore withholds only modeled arterial conclusions rather
    than suppressing observed VBG, chemistry, or longitudinal context.
    """

    if not isinstance(request, VbgExplorerRequest):
        raise TypeError("request must be VbgExplorerRequest.")
    normalized = normalize_request(request)
    candidate_region = calculate_candidate_arterial_region(
        request,
        normalized_input=normalized,
    )
    state_space = enumerate_candidate_state_space(candidate_region)
    chemistry = calculate_chemistry_interpretation(
        normalized.current_chemistry,
        current_vbg=normalized.current_vbg,
    )
    longitudinal = build_longitudinal_context(normalized.prior_observation)
    limitations = _all_limitations(
        candidate_region=candidate_region,
        state_status=state_space.enumeration_status,
        chemistry=chemistry.limitation_codes,
        longitudinal=longitudinal.limitation_codes,
    )
    return VbgExplorerResult(
        normalized_input=normalized,
        observed_vbg=normalized.current_vbg,
        candidate_arterial_region=candidate_region,
        state_space=state_space,
        chemistry=chemistry,
        longitudinal_context=longitudinal,
        limitations=limitations,
        information_that_would_reduce_ambiguity=_information_needs(
            candidate_region=candidate_region,
            chemistry=chemistry.limitation_codes,
            prior_present=normalized.prior_observation is not None,
            state_status=state_space.enumeration_status,
        ),
        provenance=explorer_provenance(),
    )


def _all_limitations(
    *,
    candidate_region: CandidateArterialRegion,
    state_status: StateEnumerationStatus,
    chemistry: tuple[LimitationCode, ...],
    longitudinal: tuple[LimitationCode, ...],
) -> tuple[LimitationCode, ...]:
    limitations = [LimitationCode.NO_ARTERIAL_OXYGENATION_INFERENCE_FROM_VBG]
    limitations.extend(candidate_region.limitation_codes)
    limitations.extend(chemistry)
    limitations.extend(longitudinal)
    if state_status is StateEnumerationStatus.CERTIFICATION_FAILED:
        limitations.append(LimitationCode.BOSTON_STATE_SPACE_CERTIFICATION_FAILED)
    return tuple(dict.fromkeys(limitations))


def _information_needs(
    *,
    candidate_region: CandidateArterialRegion,
    chemistry: tuple[LimitationCode, ...],
    prior_present: bool,
    state_status: StateEnumerationStatus,
) -> tuple[InformationNeedCode, ...]:
    needs: list[InformationNeedCode] = []
    if candidate_region.status is not CandidateRegionStatus.AVAILABLE:
        needs.append(InformationNeedCode.ARTERIAL_BLOOD_GAS_IF_ARTERIAL_CONFIRMATION_REQUIRED)
    for reason in candidate_region.reason_codes:
        needs.extend(_need_for_candidate_reason(reason))
    if LimitationCode.ALBUMIN_CORRECTION_NOT_EVALUABLE in chemistry or (
        LimitationCode.ALBUMIN_REQUIRED_FOR_STEWART_PARTITION in chemistry
    ):
        needs.append(InformationNeedCode.ALBUMIN)
    if LimitationCode.BASE_EXCESS_REQUIRED_FOR_STEWART_PARTITION in chemistry:
        needs.append(InformationNeedCode.BASE_EXCESS)
    if not prior_present:
        needs.append(InformationNeedCode.COMPARABLE_PRIOR_GAS_OR_CHEMISTRY)
    if state_status is StateEnumerationStatus.CERTIFICATION_FAILED:
        needs.append(InformationNeedCode.ARTERIAL_BLOOD_GAS_IF_ARTERIAL_CONFIRMATION_REQUIRED)
    return tuple(dict.fromkeys(needs))


def _need_for_candidate_reason(
    reason: CandidateRegionReasonCode,
) -> tuple[InformationNeedCode, ...]:
    if reason is CandidateRegionReasonCode.MISSING_SAME_SAMPLE_VENOUS_SATURATION:
        return (InformationNeedCode.SAME_SAMPLE_VENOUS_SATURATION,)
    if reason in {
        CandidateRegionReasonCode.SPECIMEN_TYPE_UNKNOWN,
        CandidateRegionReasonCode.SPECIMEN_OUTSIDE_PERIPHERAL_VENOUS_SCOPE,
        CandidateRegionReasonCode.DRAW_SITE_UNKNOWN,
        CandidateRegionReasonCode.DRAW_SITE_OUTSIDE_UPPER_EXTREMITY_SCOPE,
    }:
        return (InformationNeedCode.PERIPHERAL_UPPER_EXTREMITY_SPECIMEN_AND_SITE,)
    if reason in {
        CandidateRegionReasonCode.PERFUSION_OR_HEMODYNAMIC_STATUS_UNKNOWN,
        CandidateRegionReasonCode.KNOWN_POOR_PERFUSION_OR_HEMODYNAMIC_INSTABILITY,
    }:
        return (InformationNeedCode.PERFUSION_AND_HEMODYNAMIC_CONTEXT,)
    if reason in {
        CandidateRegionReasonCode.RECENT_VENTILATION_OR_TREATMENT_CHANGE_UNKNOWN,
        CandidateRegionReasonCode.RECENT_VENTILATION_OR_TREATMENT_CHANGE,
    }:
        return (InformationNeedCode.VENTILATION_OR_TREATMENT_CHANGE_CONTEXT,)
    if reason in {
        CandidateRegionReasonCode.PREANALYTIC_STATUS_UNKNOWN,
        CandidateRegionReasonCode.MATERIAL_PREANALYTIC_CONCERN,
    }:
        return (InformationNeedCode.PREANALYTIC_CONTEXT,)
    return (InformationNeedCode.ARTERIAL_BLOOD_GAS_IF_ARTERIAL_CONFIRMATION_REQUIRED,)
