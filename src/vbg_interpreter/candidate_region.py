"""Component-selected candidate arterial sensitivity regions.

The generic component is a deliberately broad literature-derived scenario
envelope.  It is not an individual correction, probability interval, or
claim of VBG--ABG interchangeability.  The saturation model upgrades only the
PaCO2 component when its documented applicability gates are explicitly met.
"""

from __future__ import annotations

import math

from vbg_interpreter.evidence import (
    DERIVED_AXIS_GENERIC_EVIDENCE,
    DERIVED_FARKAS_PACO2_EVIDENCE,
    FARKAS_PACO2_COEFFICIENT_MMHG_PER_PERCENTAGE_POINT,
    FARKAS_SATURATION_REFERENCE_PERCENT,
    FARKAS_SIMPLIFIED_MODEL_ID,
    GENERIC_PACO2_EVIDENCE,
    GENERIC_PACO2_LOWER_OFFSET_MMHG,
    GENERIC_PACO2_POINT_OFFSET_MMHG,
    GENERIC_PACO2_PROFILE_ID,
    GENERIC_PACO2_UPPER_OFFSET_MMHG,
    GENERIC_PERIPHERAL_OFFSET_MODEL_ID,
    GENERIC_PH_EVIDENCE,
    GENERIC_PH_LOWER_OFFSET,
    GENERIC_PH_POINT_OFFSET,
    GENERIC_PH_PROFILE_ID,
    GENERIC_PH_UPPER_OFFSET,
    GENERIC_SCENARIO_ENVELOPE_LABEL,
    PACO2_ERROR_CONVENTION,
    PACO2_EVIDENCE,
    PACO2_INTERVAL_LABEL,
    paco2_profile_for_oxygen,
)
from vbg_interpreter.models import (
    CandidateArterialPoint,
    CandidateArterialRegion,
    CandidateRegionReasonCode,
    CandidateRegionStatus,
    CandidateRegionWarningCode,
    CompletedVenousGas,
    DrawSite,
    EvidenceDescriptor,
    GasValueOrigin,
    LimitationCode,
    NormalizedExplorerInput,
    NumericInterval,
    SpecimenType,
    TriState,
    VbgExplorerRequest,
)
from vbg_interpreter.normalize import normalize_request
from vbg_interpreter.venous_gas import complete_venous_gas

_GENERIC_UNKNOWN_CONTEXT_WARNINGS = frozenset(
    {
        CandidateRegionWarningCode.GENERIC_MODEL_WITH_UNKNOWN_SPECIMEN,
        CandidateRegionWarningCode.GENERIC_MODEL_WITH_UNKNOWN_DRAW_SITE,
        CandidateRegionWarningCode.GENERIC_MODEL_WITH_UNKNOWN_PERFUSION_CONTEXT,
        CandidateRegionWarningCode.GENERIC_MODEL_WITH_UNKNOWN_VENTILATION_CONTEXT,
        CandidateRegionWarningCode.GENERIC_MODEL_WITH_UNKNOWN_PREANALYTIC_CONTEXT,
    }
)


def calculate_candidate_arterial_region(
    request: VbgExplorerRequest,
    *,
    normalized_input: NormalizedExplorerInput | None = None,
    completed_venous_gas: CompletedVenousGas | None = None,
) -> CandidateArterialRegion:
    """Return the best-supported component-specific arterial sensitivity rectangle.

    Known out-of-scope sampling or physiology suppresses arterial conclusions.
    Unknown context remains visible as a generic-model warning, never a favorable
    eligibility assertion.  The generic rectangle is a Cartesian scenario
    envelope over marginal published agreement extrema, not a joint coverage set.
    """

    normalized = normalized_input if normalized_input is not None else normalize_request(request)
    if not isinstance(normalized, NormalizedExplorerInput):
        raise TypeError("normalized_input must be NormalizedExplorerInput.")
    completed = (
        completed_venous_gas
        if completed_venous_gas is not None
        else complete_venous_gas(normalized.current_vbg)
    )
    if not isinstance(completed, CompletedVenousGas):
        raise TypeError("completed_venous_gas must be CompletedVenousGas.")

    blockers = _known_blockers(normalized)
    if blockers:
        return CandidateArterialRegion(
            status=CandidateRegionStatus.UNAVAILABLE,
            reason_codes=tuple(blockers),
        )

    ph_point = completed.ph + GENERIC_PH_POINT_OFFSET
    ph_lower = completed.ph + GENERIC_PH_LOWER_OFFSET
    ph_upper = completed.ph + GENERIC_PH_UPPER_OFFSET
    pco2_point = completed.pco2_mmhg + GENERIC_PACO2_POINT_OFFSET_MMHG
    pco2_lower = completed.pco2_mmhg + GENERIC_PACO2_LOWER_OFFSET_MMHG
    pco2_upper = completed.pco2_mmhg + GENERIC_PACO2_UPPER_OFFSET_MMHG
    ph_evidence = _generic_component_evidence(completed.ph_origin)
    paco2_evidence = _generic_component_evidence(completed.pco2_origin, pco2=True)
    paco2_model_id = GENERIC_PERIPHERAL_OFFSET_MODEL_ID
    paco2_profile_id = GENERIC_PACO2_PROFILE_ID
    warnings = _generic_warnings(normalized)

    if _farkas_paco2_eligible(normalized):
        saturation = normalized.current_vbg.venous_o2_saturation
        if saturation is None:  # pragma: no cover - eligibility guard
            raise AssertionError("Eligible Farkas model requires saturation.")
        profile = paco2_profile_for_oxygen(normalized.context.supplemental_oxygen)
        delta = FARKAS_SATURATION_REFERENCE_PERCENT - saturation.normalized_percentage_points
        pco2_point = (
            completed.pco2_mmhg + FARKAS_PACO2_COEFFICIENT_MMHG_PER_PERCENTAGE_POINT * delta
        )
        pco2_lower = pco2_point - profile.error_loa_upper_mmhg
        pco2_upper = pco2_point - profile.error_loa_lower_mmhg
        paco2_evidence = (
            PACO2_EVIDENCE
            if completed.pco2_origin is GasValueOrigin.SUPPLIED
            else DERIVED_FARKAS_PACO2_EVIDENCE
        )
        paco2_model_id = FARKAS_SIMPLIFIED_MODEL_ID
        paco2_profile_id = profile.profile_id
        if saturation.normalized_percentage_points > FARKAS_SATURATION_REFERENCE_PERCENT:
            warnings.append(CandidateRegionWarningCode.SATURATION_ABOVE_SIMPLIFIED_REFERENCE)

    domain_failure = _domain_failure(
        estimated_ph=ph_point,
        estimated_paco2=pco2_point,
        ph_lower=ph_lower,
        ph_upper=ph_upper,
        paco2_lower=pco2_lower,
        paco2_upper=pco2_upper,
    )
    if domain_failure is not None:
        return CandidateArterialRegion(
            status=CandidateRegionStatus.MODEL_DOMAIN_REFUSAL,
            reason_codes=(domain_failure,),
            ph_evidence=ph_evidence,
            paco2_evidence=paco2_evidence,
            ph_model_id=GENERIC_PERIPHERAL_OFFSET_MODEL_ID,
            paco2_model_id=paco2_model_id,
            ph_profile_id=GENERIC_PH_PROFILE_ID,
            paco2_profile_id=paco2_profile_id,
        )

    limitations: list[LimitationCode] = [
        LimitationCode.SOURCE_SPECTRUM_NOT_ESTABLISHED,
        LimitationCode.GENERIC_POPULATION_OFFSET_NOT_INDIVIDUAL_CORRECTION,
        LimitationCode.GENERIC_STUDY_RANGE_NOT_CALIBRATED_PREDICTION_INTERVAL,
        LimitationCode.GENERIC_AXES_NOT_JOINTLY_VALIDATED,
    ]
    if any(warning in _GENERIC_UNKNOWN_CONTEXT_WARNINGS for warning in warnings):
        limitations.append(LimitationCode.GENERIC_SOURCE_APPLICABILITY_UNKNOWN)
    if (
        completed.ph_origin is not GasValueOrigin.SUPPLIED
        or completed.pco2_origin is not GasValueOrigin.SUPPLIED
    ):
        limitations.append(LimitationCode.DERIVED_VENOUS_AXIS_OUTSIDE_POPULATION_MODEL_EVALUATION)

    return CandidateArterialRegion(
        status=CandidateRegionStatus.AVAILABLE,
        point=CandidateArterialPoint(ph=ph_point, paco2_mmhg=pco2_point),
        ph_interval=NumericInterval(
            lower=ph_lower,
            upper=ph_upper,
            profile_id=GENERIC_PH_PROFILE_ID,
            label=GENERIC_SCENARIO_ENVELOPE_LABEL,
            evidence_tier=ph_evidence.evidence_tier,
        ),
        paco2_interval=NumericInterval(
            lower=pco2_lower,
            upper=pco2_upper,
            profile_id=paco2_profile_id,
            label=(
                PACO2_INTERVAL_LABEL
                if paco2_model_id == FARKAS_SIMPLIFIED_MODEL_ID
                else GENERIC_SCENARIO_ENVELOPE_LABEL
            ),
            evidence_tier=paco2_evidence.evidence_tier,
            error_convention=(
                PACO2_ERROR_CONVENTION
                if paco2_model_id == FARKAS_SIMPLIFIED_MODEL_ID
                else "venous_minus_arterial_source_extrema"
            ),
        ),
        ph_evidence=ph_evidence,
        paco2_evidence=paco2_evidence,
        ph_model_id=GENERIC_PERIPHERAL_OFFSET_MODEL_ID,
        paco2_model_id=paco2_model_id,
        ph_profile_id=GENERIC_PH_PROFILE_ID,
        paco2_profile_id=paco2_profile_id,
        warning_codes=tuple(dict.fromkeys(warnings)),
        limitation_codes=tuple(dict.fromkeys(limitations)),
    )


def candidate_region_information_needs(
    region: CandidateArterialRegion,
) -> tuple[CandidateRegionReasonCode, ...]:
    """Expose typed blockers for a caller-owned information-gain list."""

    if not isinstance(region, CandidateArterialRegion):
        raise TypeError("region must be CandidateArterialRegion.")
    return region.reason_codes


def _generic_component_evidence(
    origin: GasValueOrigin, *, pco2: bool = False
) -> EvidenceDescriptor:
    if origin is GasValueOrigin.SUPPLIED:
        return GENERIC_PACO2_EVIDENCE if pco2 else GENERIC_PH_EVIDENCE
    return DERIVED_AXIS_GENERIC_EVIDENCE


def _known_blockers(value: NormalizedExplorerInput) -> list[CandidateRegionReasonCode]:
    vbg = value.current_vbg
    context = value.context
    reasons: list[CandidateRegionReasonCode] = []
    if vbg.specimen_type not in {SpecimenType.UNKNOWN, SpecimenType.PERIPHERAL_VENOUS}:
        reasons.append(CandidateRegionReasonCode.SPECIMEN_OUTSIDE_PERIPHERAL_VENOUS_SCOPE)
    if vbg.draw_site in {DrawSite.CENTRAL_CATHETER, DrawSite.PULMONARY_ARTERY_CATHETER}:
        reasons.append(CandidateRegionReasonCode.DRAW_SITE_OUTSIDE_UPPER_EXTREMITY_SCOPE)
    if context.known_poor_perfusion_or_hemodynamic_instability is TriState.YES:
        reasons.append(CandidateRegionReasonCode.KNOWN_POOR_PERFUSION_OR_HEMODYNAMIC_INSTABILITY)
    if context.recent_major_ventilation_or_treatment_change is TriState.YES:
        reasons.append(CandidateRegionReasonCode.RECENT_VENTILATION_OR_TREATMENT_CHANGE)
    if context.material_preanalytic_concern is TriState.YES:
        reasons.append(CandidateRegionReasonCode.MATERIAL_PREANALYTIC_CONCERN)
    return reasons


def _generic_warnings(value: NormalizedExplorerInput) -> list[CandidateRegionWarningCode]:
    vbg = value.current_vbg
    context = value.context
    warnings: list[CandidateRegionWarningCode] = []
    if vbg.specimen_type is SpecimenType.UNKNOWN:
        warnings.append(CandidateRegionWarningCode.GENERIC_MODEL_WITH_UNKNOWN_SPECIMEN)
    if vbg.draw_site is DrawSite.UNKNOWN:
        warnings.append(CandidateRegionWarningCode.GENERIC_MODEL_WITH_UNKNOWN_DRAW_SITE)
    if context.known_poor_perfusion_or_hemodynamic_instability is TriState.UNKNOWN:
        warnings.append(CandidateRegionWarningCode.GENERIC_MODEL_WITH_UNKNOWN_PERFUSION_CONTEXT)
    if context.recent_major_ventilation_or_treatment_change is TriState.UNKNOWN:
        warnings.append(CandidateRegionWarningCode.GENERIC_MODEL_WITH_UNKNOWN_VENTILATION_CONTEXT)
    if context.material_preanalytic_concern is TriState.UNKNOWN:
        warnings.append(CandidateRegionWarningCode.GENERIC_MODEL_WITH_UNKNOWN_PREANALYTIC_CONTEXT)
    return warnings


def same_sample_saturation_would_enable_farkas_paco2(
    value: NormalizedExplorerInput,
) -> bool:
    """Return whether saturation is the only missing PaCO2-upgrade gate."""

    if not isinstance(value, NormalizedExplorerInput):
        raise TypeError("value must be NormalizedExplorerInput.")
    return value.current_vbg.venous_o2_saturation is None and _farkas_non_saturation_gates_pass(
        value
    )


def _farkas_paco2_eligible(value: NormalizedExplorerInput) -> bool:
    return value.current_vbg.venous_o2_saturation is not None and _farkas_non_saturation_gates_pass(
        value
    )


def _farkas_non_saturation_gates_pass(value: NormalizedExplorerInput) -> bool:
    vbg = value.current_vbg
    context = value.context
    return (
        vbg.specimen_type is SpecimenType.PERIPHERAL_VENOUS
        and vbg.draw_site is DrawSite.UPPER_EXTREMITY_PERIPHERAL
        and context.known_poor_perfusion_or_hemodynamic_instability is TriState.NO
        and context.recent_major_ventilation_or_treatment_change is TriState.NO
        and context.material_preanalytic_concern is TriState.NO
    )


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
