"""Scientific checks for the exhaustive set-valued state-space lane."""

from __future__ import annotations

import pytest

from vbg_interpreter.certified_envelope import signature_from_continuous_hh_point
from vbg_interpreter.models import (
    AcidBaseStateCode,
    CandidateArterialPoint,
    CandidateArterialRegion,
    CandidateRegionReasonCode,
    CandidateRegionStatus,
    ChronicityBranch,
    EvidenceDescriptor,
    EvidenceTier,
    ExpectedCompensationCode,
    FeatureConclusionStatus,
    MeasuredVsExpectedCode,
    NumericInterval,
    PrimaryProcessCode,
    StateEnumerationStatus,
    StateSignature,
    StateSpaceResult,
)
from vbg_interpreter.state_space import (
    enumerate_candidate_state_space,
    feature_conclusions_for_signatures,
)


def _region(
    *,
    point_ph: float = 7.441417434223236,
    point_paco2: float = 38.43909794885929,
    ph_lower: float = 7.411417434223236,
    ph_upper: float = 7.471417434223237,
    paco2_lower: float = 29.239097948859293,
    paco2_upper: float = 47.179097948859294,
) -> CandidateArterialRegion:
    return CandidateArterialRegion(
        status=CandidateRegionStatus.AVAILABLE,
        point=CandidateArterialPoint(ph=point_ph, paco2_mmhg=point_paco2),
        ph_interval=NumericInterval(
            lower=ph_lower,
            upper=ph_upper,
            profile_id="test-ph-profile",
            label="test pH sensitivity range",
            evidence_tier=EvidenceTier.DERIVATION_ONLY,
        ),
        paco2_interval=NumericInterval(
            lower=paco2_lower,
            upper=paco2_upper,
            profile_id="test-paco2-profile",
            label="test PaCO2 sensitivity range",
            evidence_tier=EvidenceTier.EXTERNALLY_EVALUATED,
        ),
        ph_evidence=EvidenceDescriptor(
            evidence_tier=EvidenceTier.DERIVATION_ONLY,
            external_validation=False,
            source_ids=("test",),
        ),
        paco2_evidence=EvidenceDescriptor(
            evidence_tier=EvidenceTier.EXTERNALLY_EVALUATED,
            external_validation=True,
            source_ids=("test",),
        ),
        uncertainty_profile_id="test-profile",
    )


def test_certified_envelope_includes_the_previous_grid_counterexample() -> None:
    """The known omitted state is found without treating any display sample as proof."""

    result = enumerate_candidate_state_space(_region())

    expected = StateSignature(
        acid_base_state=AcidBaseStateCode.NEAR_NORMAL,
        primary_process=PrimaryProcessCode.NEAR_NORMAL_RESPIRATORY_ACIDOSIS_OR_MIXED,
        expected_compensation=ExpectedCompensationCode.RESPIRATORY_ACIDOSIS_HCO3_GUIDES,
        measured_vs_expected=MeasuredVsExpectedCode.WITHIN_EXPECTED,
        mixed_disorder_flag=False,
        chronicity_branch=ChronicityBranch.NOT_CHRONIC_FLAGGED,
    )
    assert expected in result.possible_signatures
    assert result.coverage_method_id == "CERTIFIED_TERMINAL_PATH_FEASIBILITY"
    assert result.decision_surface_count == 16
    assert result.terminal_path_count == 54
    assert result.coordinate_view is not None
    assert len(result.coordinate_view.samples) == 17**2


def test_certified_signatures_are_deterministic_across_repeated_traversal() -> None:
    first = enumerate_candidate_state_space(_region())
    second = enumerate_candidate_state_space(_region())

    assert first.to_dict() == second.to_dict()


def test_feature_predicates_map_all_some_and_none_exactly() -> None:
    all_acidemia = StateSignature(
        acid_base_state=AcidBaseStateCode.ACIDEMIA,
        primary_process=PrimaryProcessCode.METABOLIC_ACIDOSIS,
        expected_compensation=ExpectedCompensationCode.WINTERS_PACO2_RANGE,
        measured_vs_expected=MeasuredVsExpectedCode.WITHIN_EXPECTED,
        mixed_disorder_flag=False,
        chronicity_branch=ChronicityBranch.NOT_CHRONIC_FLAGGED,
    )
    some_mixed = StateSignature(
        acid_base_state=AcidBaseStateCode.ACIDEMIA,
        primary_process=PrimaryProcessCode.METABOLIC_ACIDOSIS,
        expected_compensation=ExpectedCompensationCode.WINTERS_PACO2_RANGE,
        measured_vs_expected=MeasuredVsExpectedCode.ABOVE_EXPECTED,
        mixed_disorder_flag=True,
        chronicity_branch=ChronicityBranch.CHRONIC_FLAGGED,
    )

    conclusions = {
        item.feature_id: item.status
        for item in feature_conclusions_for_signatures((all_acidemia, some_mixed))
    }

    assert conclusions["ACIDEMIA"] is FeatureConclusionStatus.PRESENT_ACROSS_ALL_MODELED_STATES
    assert (
        conclusions["MIXED_PROCESS_FLAG"] is FeatureConclusionStatus.POSSIBLE_IN_SOME_MODELED_STATES
    )
    assert (
        conclusions["EXPECTED_COMPENSATION_WINTERS_PACO2_RANGE"]
        is FeatureConclusionStatus.PRESENT_ACROSS_ALL_MODELED_STATES
    )
    assert (
        conclusions["MEASURED_VS_EXPECTED_WITHIN_EXPECTED"]
        is FeatureConclusionStatus.POSSIBLE_IN_SOME_MODELED_STATES
    )
    assert conclusions["ALKALEMIA"] is FeatureConclusionStatus.EXCLUDED_WITHIN_MODELED_STATE_SPACE


@pytest.mark.parametrize(
    ("measured", "feature_id"),
    (
        (MeasuredVsExpectedCode.BELOW_EXPECTED, "METABOLIC_ACIDOSIS_COMPONENT"),
        (MeasuredVsExpectedCode.ABOVE_EXPECTED, "METABOLIC_ALKALOSIS_COMPONENT"),
    ),
)
def test_mixed_respiratory_alkalosis_retains_the_corresponding_metabolic_component(
    measured: MeasuredVsExpectedCode,
    feature_id: str,
) -> None:
    signature = StateSignature(
        acid_base_state=AcidBaseStateCode.ALKALEMIA,
        primary_process=PrimaryProcessCode.RESPIRATORY_ALKALOSIS,
        expected_compensation=ExpectedCompensationCode.RESPIRATORY_ALKALOSIS_HCO3_GUIDES,
        measured_vs_expected=measured,
        mixed_disorder_flag=True,
        chronicity_branch=ChronicityBranch.NOT_CHRONIC_FLAGGED,
    )

    conclusions = {
        item.feature_id: item.status for item in feature_conclusions_for_signatures((signature,))
    }

    assert conclusions[feature_id] is FeatureConclusionStatus.PRESENT_ACROSS_ALL_MODELED_STATES


def test_ambiguous_near_normal_signature_cannot_exclude_components() -> None:
    rule_signature = signature_from_continuous_hh_point(
        ph=7.35,
        paco2_mmhg=38.0,
        chronicity_branch=ChronicityBranch.NOT_CHRONIC_FLAGGED,
    )
    signature = StateSignature(
        acid_base_state=rule_signature.acid_base_state,
        primary_process=rule_signature.primary_process,
        expected_compensation=rule_signature.expected_compensation,
        measured_vs_expected=rule_signature.measured_vs_expected,
        mixed_disorder_flag=rule_signature.mixed_disorder_flag,
        chronicity_branch=ChronicityBranch.NOT_CHRONIC_FLAGGED,
    )

    conclusions = {
        item.feature_id: item.status for item in feature_conclusions_for_signatures((signature,))
    }

    assert signature.primary_process is PrimaryProcessCode.NEAR_NORMAL_COMPENSATED_OR_MIXED
    assert signature.mixed_disorder_flag is True
    assert {
        conclusions[feature_id]
        for feature_id in (
            "METABOLIC_ACIDOSIS_COMPONENT",
            "METABOLIC_ALKALOSIS_COMPONENT",
            "RESPIRATORY_ACIDOSIS_COMPONENT",
            "RESPIRATORY_ALKALOSIS_COMPONENT",
        )
    } == {FeatureConclusionStatus.NOT_EVALUABLE}


def test_unavailable_region_marks_every_feature_not_evaluable() -> None:
    result = enumerate_candidate_state_space(
        CandidateArterialRegion(
            status=CandidateRegionStatus.UNAVAILABLE,
            reason_codes=(CandidateRegionReasonCode.MISSING_SAME_SAMPLE_VENOUS_SATURATION,),
        )
    )

    assert result.enumeration_status is StateEnumerationStatus.NOT_EVALUATED
    assert not result.possible_signatures
    assert result.feature_conclusions
    assert {conclusion.status for conclusion in result.feature_conclusions} == {
        FeatureConclusionStatus.NOT_EVALUABLE
    }


def test_public_not_evaluated_constructor_keeps_the_complete_feature_contract() -> None:
    result = StateSpaceResult.not_evaluated()

    assert result.enumeration_status is StateEnumerationStatus.NOT_EVALUATED
    assert result.feature_conclusions
    assert {conclusion.status for conclusion in result.feature_conclusions} == {
        FeatureConclusionStatus.NOT_EVALUABLE
    }
