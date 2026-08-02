"""Certified, set-valued acid--base state enumeration for the explorer.

The terminal-path engine is the scientific inference mechanism.  The small
coordinate display grid returned here is deliberately explanatory only: no
inference, containment decision, or set predicate is derived from its samples.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from vbg_interpreter.certified_envelope import (
    COVERAGE_METHOD_ID,
    BostonEnvelopeCertificationError,
    certify_boston_envelope,
    signature_from_continuous_hh_point,
)
from vbg_interpreter.models import (
    STATE_FEATURE_IDS,
    AcidBaseStateCode,
    CandidateArterialRegion,
    CandidateRegionStatus,
    ChronicityBranch,
    CoordinateDisplaySample,
    CoordinateStateSpaceView,
    ExpectedCompensationCode,
    FeatureConclusion,
    FeatureConclusionStatus,
    MeasuredVsExpectedCode,
    PrimaryProcessCode,
    StateEnumerationStatus,
    StateSignature,
    StateSpaceResult,
)
from vbg_interpreter.state_categories import RuleSignature

COORDINATE_DISPLAY_GRID_RESOLUTION = 17
_COMPONENT_FEATURE_IDS = frozenset(
    {
        "METABOLIC_ACIDOSIS_COMPONENT",
        "METABOLIC_ALKALOSIS_COMPONENT",
        "RESPIRATORY_ACIDOSIS_COMPONENT",
        "RESPIRATORY_ALKALOSIS_COMPONENT",
    }
)
_COMPONENT_AMBIGUOUS_PRIMARY_PROCESSES = frozenset(
    {
        PrimaryProcessCode.ACIDEMIA_UNCLEAR,
        PrimaryProcessCode.ALKALEMIA_UNCLEAR,
        PrimaryProcessCode.NEAR_NORMAL_COMPENSATED_OR_MIXED,
        PrimaryProcessCode.NO_CLEAR_PRIMARY_PROCESS,
    }
)


def enumerate_candidate_state_space(region: CandidateArterialRegion) -> StateSpaceResult:
    """Return every feasible compatibility-ruleset state or fail closed.

    A candidate region which is unavailable simply has no modeled state space;
    observed VBG and chemistry lanes remain usable by the caller.  If the
    terminal-path proof cannot finish, no partial set or set-theoretic conclusion
    is returned.
    """

    if not isinstance(region, CandidateArterialRegion):
        raise TypeError("region must be CandidateArterialRegion.")
    if region.status is not CandidateRegionStatus.AVAILABLE:
        return _not_evaluated_state_space(StateEnumerationStatus.NOT_EVALUATED)
    if (
        region.point is None or region.ph_interval is None or region.paco2_interval is None
    ):  # pragma: no cover - protected by CandidateArterialRegion
        raise AssertionError("Available region must include complete numeric payload.")

    try:
        certification = certify_boston_envelope(
            ph_lower=region.ph_interval.lower,
            ph_upper=region.ph_interval.upper,
            paco2_lower=region.paco2_interval.lower,
            paco2_upper=region.paco2_interval.upper,
            branches=tuple(ChronicityBranch),
        )
        signatures = _canonical_signatures(
            _to_state_signature(rule, branch)
            for branch_set in certification.branches
            for rule in branch_set.signatures
            for branch in (branch_set.chronicity_branch,)
        )
        coordinate_view = _coordinate_view(region)
    except BostonEnvelopeCertificationError:
        return _not_evaluated_state_space(StateEnumerationStatus.CERTIFICATION_FAILED)

    return StateSpaceResult(
        enumeration_status=StateEnumerationStatus.CERTIFIED_EXHAUSTIVE,
        possible_signatures=signatures,
        feature_conclusions=feature_conclusions_for_signatures(signatures),
        modeled_point=region.point,
        coverage_method_id=COVERAGE_METHOD_ID,
        decision_surface_count=certification.decision_surface_count,
        terminal_path_count=certification.terminal_path_count,
        certification_precision_digits=certification.certification_precision_digits,
        coordinate_view=coordinate_view,
    )


def _to_state_signature(
    rule: RuleSignature,
    chronicity_branch: ChronicityBranch,
) -> StateSignature:
    return StateSignature(
        acid_base_state=rule.acid_base_state,
        primary_process=rule.primary_process,
        expected_compensation=rule.expected_compensation,
        measured_vs_expected=rule.measured_vs_expected,
        mixed_disorder_flag=rule.mixed_disorder_flag,
        chronicity_branch=chronicity_branch,
    )


def _signature_sort_key(value: StateSignature) -> tuple[int, int, int, int, bool, int]:
    return (
        tuple(AcidBaseStateCode).index(value.acid_base_state),
        tuple(PrimaryProcessCode).index(value.primary_process),
        tuple(ExpectedCompensationCode).index(value.expected_compensation),
        tuple(MeasuredVsExpectedCode).index(value.measured_vs_expected),
        value.mixed_disorder_flag,
        tuple(ChronicityBranch).index(value.chronicity_branch),
    )


def _canonical_signatures(values: Iterable[StateSignature]) -> tuple[StateSignature, ...]:
    signatures = tuple(values)
    if not all(isinstance(value, StateSignature) for value in signatures):
        raise TypeError("State-space signatures must be StateSignature.")
    return tuple(sorted(set(signatures), key=_signature_sort_key))


def _coordinate_view(region: CandidateArterialRegion) -> CoordinateStateSpaceView:
    """Build a deterministic display map after the exhaustive proof succeeds."""

    if region.ph_interval is None or region.paco2_interval is None:
        raise AssertionError("Coordinate view requires candidate intervals.")
    ph_values = _display_axis(
        region.ph_interval.lower,
        region.ph_interval.upper,
        COORDINATE_DISPLAY_GRID_RESOLUTION,
    )
    paco2_values = _display_axis(
        region.paco2_interval.lower,
        region.paco2_interval.upper,
        COORDINATE_DISPLAY_GRID_RESOLUTION,
    )
    samples = tuple(
        CoordinateDisplaySample(
            ph=ph,
            paco2_mmhg=paco2,
            signatures=_canonical_signatures(
                _to_state_signature(
                    signature_from_continuous_hh_point(
                        ph=ph,
                        paco2_mmhg=paco2,
                        chronicity_branch=branch,
                    ),
                    branch,
                )
                for branch in ChronicityBranch
            ),
        )
        for ph in ph_values
        for paco2 in paco2_values
    )
    return CoordinateStateSpaceView(
        display_grid_resolution=COORDINATE_DISPLAY_GRID_RESOLUTION,
        samples=samples,
    )


def _display_axis(lower: float, upper: float, resolution: int) -> tuple[float, ...]:
    increment = (upper - lower) / (resolution - 1)
    return tuple(lower + index * increment for index in range(resolution))


def feature_conclusions_for_signatures(
    signatures: tuple[StateSignature, ...],
) -> tuple[FeatureConclusion, ...]:
    """Project a supplied nonempty state set into the explorer's exact predicates."""

    if not signatures:
        raise ValueError("Feature conclusions require at least one feasible state.")
    predicates = _feature_predicates()
    results: list[FeatureConclusion] = []
    for feature_id, predicate in predicates:
        if feature_id in _COMPONENT_FEATURE_IDS and any(
            signature.primary_process in _COMPONENT_AMBIGUOUS_PRIMARY_PROCESSES
            for signature in signatures
        ):
            status = FeatureConclusionStatus.NOT_EVALUABLE
        else:
            count = sum(1 for signature in signatures if predicate(signature))
            if count == len(signatures):
                status = FeatureConclusionStatus.PRESENT_ACROSS_ALL_MODELED_STATES
            elif count:
                status = FeatureConclusionStatus.POSSIBLE_IN_SOME_MODELED_STATES
            else:
                status = FeatureConclusionStatus.EXCLUDED_WITHIN_MODELED_STATE_SPACE
        results.append(FeatureConclusion(feature_id=feature_id, status=status))
    return tuple(results)


def _not_evaluated_state_space(status: StateEnumerationStatus) -> StateSpaceResult:
    """Return explicit non-evaluability without publishing an inferred state.

    ``NOT_EVALUABLE`` is a statement about whether a feature can be assessed,
    rather than a claim that a feature is absent.  Publishing it for every
    feature keeps the one result contract total while preserving the fail-closed
    rule that uncertified paths cannot yield possible or excluded states.
    """

    if status not in {
        StateEnumerationStatus.NOT_EVALUATED,
        StateEnumerationStatus.CERTIFICATION_FAILED,
    }:
        raise ValueError("Only non-certified state statuses are not evaluable.")
    if status is StateEnumerationStatus.NOT_EVALUATED:
        return StateSpaceResult.not_evaluated()
    return StateSpaceResult(
        enumeration_status=status,
        feature_conclusions=tuple(
            FeatureConclusion(
                feature_id=feature_id,
                status=FeatureConclusionStatus.NOT_EVALUABLE,
            )
            for feature_id in STATE_FEATURE_IDS
        ),
    )


def _feature_predicates() -> tuple[tuple[str, Callable[[StateSignature], bool]], ...]:
    acid_state = tuple(
        (
            feature_id,
            lambda value, state=state: value.acid_base_state is state,
        )
        for feature_id, state in (
            ("ACIDEMIA", AcidBaseStateCode.ACIDEMIA),
            ("NEAR_NORMAL_PH", AcidBaseStateCode.NEAR_NORMAL),
            ("ALKALEMIA", AcidBaseStateCode.ALKALEMIA),
        )
    )
    primary = tuple(
        (
            f"PRIMARY_{process.value}",
            lambda value, process=process: value.primary_process is process,
        )
        for process in PrimaryProcessCode
    )
    expected_compensation = tuple(
        (
            f"EXPECTED_COMPENSATION_{code.value}",
            lambda value, code=code: value.expected_compensation is code,
        )
        for code in ExpectedCompensationCode
    )
    measured_vs_expected = tuple(
        (
            f"MEASURED_VS_EXPECTED_{code.value}",
            lambda value, code=code: value.measured_vs_expected is code,
        )
        for code in MeasuredVsExpectedCode
    )
    predicates = (
        *acid_state,
        *primary,
        *expected_compensation,
        *measured_vs_expected,
        (
            "METABOLIC_ACIDOSIS_COMPONENT",
            lambda value: _component_presence(value, "METABOLIC_ACIDOSIS_COMPONENT"),
        ),
        (
            "METABOLIC_ALKALOSIS_COMPONENT",
            lambda value: _component_presence(value, "METABOLIC_ALKALOSIS_COMPONENT"),
        ),
        (
            "RESPIRATORY_ACIDOSIS_COMPONENT",
            lambda value: _component_presence(value, "RESPIRATORY_ACIDOSIS_COMPONENT"),
        ),
        (
            "RESPIRATORY_ALKALOSIS_COMPONENT",
            lambda value: _component_presence(value, "RESPIRATORY_ALKALOSIS_COMPONENT"),
        ),
        ("MIXED_PROCESS_FLAG", lambda value: value.mixed_disorder_flag),
        (
            "CHRONIC_FLAGGED_BRANCH",
            lambda value: value.chronicity_branch is ChronicityBranch.CHRONIC_FLAGGED,
        ),
        (
            "NOT_CHRONIC_FLAGGED_BRANCH",
            lambda value: value.chronicity_branch is ChronicityBranch.NOT_CHRONIC_FLAGGED,
        ),
    )
    if tuple(feature_id for feature_id, _ in predicates) != STATE_FEATURE_IDS:
        raise AssertionError("State feature predicates drifted from the canonical feature catalog.")
    return predicates


def _component_presence(value: StateSignature, feature_id: str) -> bool:
    """Project a compatibility-rule signature into a component-level feature.

    This does not turn an ambiguous primary label into a forced diagnosis.  It
    only recognizes an explicit primary component or an explicitly out-of-range
    compensation relationship that the ruleset marks as mixed.
    """

    primary = value.primary_process
    measured = value.measured_vs_expected
    respiratory_acidosis_primary = {
        PrimaryProcessCode.RESPIRATORY_ACIDOSIS,
        PrimaryProcessCode.NEAR_NORMAL_RESPIRATORY_ACIDOSIS_OR_MIXED,
    }
    respiratory_alkalosis_primary = {
        PrimaryProcessCode.RESPIRATORY_ALKALOSIS,
        PrimaryProcessCode.NEAR_NORMAL_RESPIRATORY_ALKALOSIS_OR_MIXED,
    }
    if feature_id == "METABOLIC_ACIDOSIS_COMPONENT":
        return primary is PrimaryProcessCode.METABOLIC_ACIDOSIS or (
            primary in respiratory_acidosis_primary | respiratory_alkalosis_primary
            and measured is MeasuredVsExpectedCode.BELOW_EXPECTED
        )
    if feature_id == "METABOLIC_ALKALOSIS_COMPONENT":
        return primary is PrimaryProcessCode.METABOLIC_ALKALOSIS or (
            primary in respiratory_acidosis_primary | respiratory_alkalosis_primary
            and measured is MeasuredVsExpectedCode.ABOVE_EXPECTED
        )
    if feature_id == "RESPIRATORY_ACIDOSIS_COMPONENT":
        return (
            primary in respiratory_acidosis_primary
            or (
                primary is PrimaryProcessCode.METABOLIC_ACIDOSIS
                and measured is MeasuredVsExpectedCode.ABOVE_EXPECTED
            )
            or (
                primary is PrimaryProcessCode.METABOLIC_ALKALOSIS
                and measured is MeasuredVsExpectedCode.ABOVE_EXPECTED
            )
        )
    if feature_id == "RESPIRATORY_ALKALOSIS_COMPONENT":
        return (
            primary in respiratory_alkalosis_primary
            or (
                primary is PrimaryProcessCode.METABOLIC_ACIDOSIS
                and measured is MeasuredVsExpectedCode.BELOW_EXPECTED
            )
            or (
                primary is PrimaryProcessCode.METABOLIC_ALKALOSIS
                and measured is MeasuredVsExpectedCode.BELOW_EXPECTED
            )
        )
    raise AssertionError("Unknown component feature.")
