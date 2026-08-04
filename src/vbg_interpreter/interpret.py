"""One public, progressive interpretation entry point for the VBG Explorer."""

from __future__ import annotations

from vbg_interpreter.candidate_region import (
    calculate_candidate_arterial_region,
    same_sample_saturation_would_enable_farkas_paco2,
)
from vbg_interpreter.chemistry import calculate_chemistry_interpretation
from vbg_interpreter.evidence import explorer_provenance
from vbg_interpreter.longitudinal import build_longitudinal_context
from vbg_interpreter.models import (
    CandidateArterialRegion,
    CandidateRegionReasonCode,
    CandidateRegionStatus,
    CandidateRegionWarningCode,
    CurrentChemistry,
    InformationNeedCode,
    LimitationCode,
    NormalizedExplorerInput,
    NormalizedVbg,
    StateEnumerationStatus,
    VbgExplorerRequest,
    VbgExplorerResult,
)
from vbg_interpreter.normalize import normalize_request
from vbg_interpreter.state_space import enumerate_candidate_state_space
from vbg_interpreter.venous_gas import complete_venous_gas, describe_venous_orientation


def interpret_vbg(request: VbgExplorerRequest) -> VbgExplorerResult:
    """Interpret one current VBG and chemistry panel without forcing a diagnosis.

    Every lane is computed independently where its requirements are met. Missing
    optional inputs therefore withhold only their dependent calculation; unknown
    arterial-model context remains an explicit generic-model caveat, while known
    blockers suppress only arterial conclusions.
    """

    if not isinstance(request, VbgExplorerRequest):
        raise TypeError("request must be VbgExplorerRequest.")
    normalized = normalize_request(request)
    completed_venous_gas = complete_venous_gas(normalized.current_vbg)
    venous_orientation = describe_venous_orientation(completed_venous_gas)
    candidate_region = calculate_candidate_arterial_region(
        request,
        normalized_input=normalized,
        completed_venous_gas=completed_venous_gas,
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
        completed_gas=completed_venous_gas.limitation_codes,
        venous_orientation=venous_orientation.limitation_codes,
        chemistry=chemistry.limitation_codes,
        longitudinal=longitudinal.limitation_codes,
    )
    return VbgExplorerResult(
        normalized_input=normalized,
        observed_vbg=normalized.current_vbg,
        completed_venous_gas=completed_venous_gas,
        venous_orientation=venous_orientation,
        candidate_arterial_region=candidate_region,
        state_space=state_space,
        chemistry=chemistry,
        longitudinal_context=longitudinal,
        limitations=limitations,
        information_that_would_reduce_ambiguity=_information_needs(
            candidate_region=candidate_region,
            model_input=normalized,
            current_vbg=normalized.current_vbg,
            chemistry=normalized.current_chemistry,
            chemistry_limitations=chemistry.limitation_codes,
            prior_present=normalized.prior_observation is not None,
            state_status=state_space.enumeration_status,
        ),
        provenance=explorer_provenance(candidate_region),
    )


def _all_limitations(
    *,
    candidate_region: CandidateArterialRegion,
    state_status: StateEnumerationStatus,
    completed_gas: tuple[LimitationCode, ...],
    venous_orientation: tuple[LimitationCode, ...],
    chemistry: tuple[LimitationCode, ...],
    longitudinal: tuple[LimitationCode, ...],
) -> tuple[LimitationCode, ...]:
    limitations = [LimitationCode.NO_ARTERIAL_OXYGENATION_INFERENCE_FROM_VBG]
    limitations.extend(completed_gas)
    limitations.extend(venous_orientation)
    limitations.extend(candidate_region.limitation_codes)
    limitations.extend(chemistry)
    limitations.extend(longitudinal)
    if state_status is StateEnumerationStatus.CERTIFICATION_FAILED:
        limitations.append(LimitationCode.BOSTON_STATE_SPACE_CERTIFICATION_FAILED)
    return tuple(dict.fromkeys(limitations))


def _information_needs(
    *,
    candidate_region: CandidateArterialRegion,
    model_input: NormalizedExplorerInput,
    current_vbg: NormalizedVbg,
    chemistry: CurrentChemistry,
    chemistry_limitations: tuple[LimitationCode, ...],
    prior_present: bool,
    state_status: StateEnumerationStatus,
) -> tuple[InformationNeedCode, ...]:
    needs: list[InformationNeedCode] = []
    if candidate_region.status is not CandidateRegionStatus.AVAILABLE:
        needs.append(InformationNeedCode.ARTERIAL_BLOOD_GAS_IF_ARTERIAL_CONFIRMATION_REQUIRED)
    if current_vbg.ph is None:
        needs.append(InformationNeedCode.MEASURED_VENOUS_PH)
    if current_vbg.pco2_mmhg is None:
        needs.append(InformationNeedCode.MEASURED_VENOUS_PCO2)
    if same_sample_saturation_would_enable_farkas_paco2(model_input):
        needs.append(InformationNeedCode.SAME_SAMPLE_VENOUS_SATURATION)
    for reason in candidate_region.reason_codes:
        needs.extend(_need_for_candidate_reason(reason))
    if chemistry.albumin_g_l is None and (
        LimitationCode.ALBUMIN_CORRECTION_NOT_EVALUABLE in chemistry_limitations
        or LimitationCode.ALBUMIN_REQUIRED_FOR_STEWART_PARTITION in chemistry_limitations
    ):
        needs.append(InformationNeedCode.ALBUMIN)
    if LimitationCode.BASE_EXCESS_REQUIRED_FOR_STEWART_PARTITION in chemistry_limitations:
        needs.append(InformationNeedCode.BASE_EXCESS)
    if chemistry.sodium_mmol_l is None:
        needs.append(InformationNeedCode.SODIUM)
    if chemistry.chloride_mmol_l is None:
        needs.append(InformationNeedCode.CHLORIDE)
    if chemistry.serum_total_co2_mmol_l is None:
        needs.append(InformationNeedCode.SERUM_TOTAL_CO2)
    for warning in candidate_region.warning_codes:
        needs.extend(_need_for_candidate_warning(warning))
    if not prior_present:
        needs.append(InformationNeedCode.COMPARABLE_PRIOR_GAS_OR_CHEMISTRY)
    if state_status is StateEnumerationStatus.CERTIFICATION_FAILED:
        needs.append(InformationNeedCode.ARTERIAL_BLOOD_GAS_IF_ARTERIAL_CONFIRMATION_REQUIRED)
    return tuple(dict.fromkeys(needs))


def _need_for_candidate_warning(
    warning: CandidateRegionWarningCode,
) -> tuple[InformationNeedCode, ...]:
    if warning is CandidateRegionWarningCode.GENERIC_MODEL_WITH_UNKNOWN_SPECIMEN:
        return (InformationNeedCode.PERIPHERAL_UPPER_EXTREMITY_SPECIMEN_AND_SITE,)
    if warning is CandidateRegionWarningCode.GENERIC_MODEL_WITH_UNKNOWN_DRAW_SITE:
        return (InformationNeedCode.PERIPHERAL_UPPER_EXTREMITY_SPECIMEN_AND_SITE,)
    if warning is CandidateRegionWarningCode.GENERIC_MODEL_WITH_UNKNOWN_PERFUSION_CONTEXT:
        return (InformationNeedCode.PERFUSION_AND_HEMODYNAMIC_CONTEXT,)
    if warning is CandidateRegionWarningCode.GENERIC_MODEL_WITH_UNKNOWN_VENTILATION_CONTEXT:
        return (InformationNeedCode.VENTILATION_OR_TREATMENT_CHANGE_CONTEXT,)
    if warning is CandidateRegionWarningCode.GENERIC_MODEL_WITH_UNKNOWN_PREANALYTIC_CONTEXT:
        return (InformationNeedCode.PREANALYTIC_CONTEXT,)
    return ()


def _need_for_candidate_reason(
    reason: CandidateRegionReasonCode,
) -> tuple[InformationNeedCode, ...]:
    if reason in {
        CandidateRegionReasonCode.SPECIMEN_OUTSIDE_PERIPHERAL_VENOUS_SCOPE,
        CandidateRegionReasonCode.DRAW_SITE_OUTSIDE_UPPER_EXTREMITY_SCOPE,
    }:
        return (InformationNeedCode.PERIPHERAL_UPPER_EXTREMITY_SPECIMEN_AND_SITE,)
    if reason in {
        CandidateRegionReasonCode.KNOWN_POOR_PERFUSION_OR_HEMODYNAMIC_INSTABILITY,
        CandidateRegionReasonCode.RECENT_VENTILATION_OR_TREATMENT_CHANGE,
        CandidateRegionReasonCode.MATERIAL_PREANALYTIC_CONCERN,
    }:
        return ()
    return (InformationNeedCode.ARTERIAL_BLOOD_GAS_IF_ARTERIAL_CONFIRMATION_REQUIRED,)
