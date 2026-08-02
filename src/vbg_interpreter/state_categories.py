"""Stable Boston categories from explicit decision-surface signs.

This module is deliberately independent of the numerical-envelope traversal.
Continuous-real VBG point, validation, and envelope paths all use the same
categorical projection.  The compatibility-protected legacy ABG implementation
remains separate and is not the certified VBG numerical semantics.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from vbg_interpreter.models import (
    AcidBaseStateCode,
    ChronicityBranch,
    ExpectedCompensationCode,
    MeasuredVsExpectedCode,
    PrimaryProcessCode,
)


@dataclass(frozen=True, slots=True)
class RuleSignature:
    """Categorical state before its chronicity branch is attached."""

    acid_base_state: AcidBaseStateCode
    primary_process: PrimaryProcessCode
    expected_compensation: ExpectedCompensationCode
    measured_vs_expected: MeasuredVsExpectedCode
    mixed_disorder_flag: bool


# Keep the compact certified-envelope implementation readable while making the
# new Explorer types the sole public contract.
BostonChronicityBranch = ChronicityBranch
BostonClassificationSignature = RuleSignature

DECISION_SURFACE_IDS = (
    "ph_7_35",
    "ph_7_45",
    "paco2_38",
    "paco2_42",
    "hco3_22",
    "hco3_26",
    "winters_lower",
    "winters_upper",
    "metabolic_alkalosis_lower",
    "metabolic_alkalosis_upper",
    "respiratory_acidosis_chronic_lower",
    "respiratory_acidosis_chronic_upper",
    "respiratory_acidosis_unflagged_lower",
    "respiratory_acidosis_unflagged_upper",
    "respiratory_alkalosis_lower",
    "respiratory_alkalosis_upper",
)


def _require_signs(signs: Mapping[str, int]) -> None:
    if set(signs) != set(DECISION_SURFACE_IDS):
        raise ValueError("Boston decision signs must contain the canonical surface catalog.")
    if any(value not in {-1, 0, 1} for value in signs.values()):
        raise ValueError("Boston decision signs must be -1, 0, or 1.")


def _comparison_category(
    *,
    lower_sign: int,
    upper_sign: int,
    orientation: str,
) -> tuple[MeasuredVsExpectedCode, bool]:
    if orientation == "measured_minus_expected":
        if lower_sign < 0:
            return MeasuredVsExpectedCode.BELOW_EXPECTED, True
        if upper_sign > 0:
            return MeasuredVsExpectedCode.ABOVE_EXPECTED, True
    elif orientation == "hco3_minus_expected":
        if lower_sign < 0:
            return MeasuredVsExpectedCode.BELOW_EXPECTED, True
        if upper_sign > 0:
            return MeasuredVsExpectedCode.ABOVE_EXPECTED, True
    else:  # pragma: no cover - internal programmer guard
        raise ValueError("Unknown Boston comparison orientation.")
    return MeasuredVsExpectedCode.WITHIN_EXPECTED, False


def signature_from_surface_signs(
    signs: Mapping[str, int],
    *,
    chronicity_branch: BostonChronicityBranch,
) -> BostonClassificationSignature:
    """Project the complete decision-surface sign vector to stable categories."""

    _require_signs(signs)
    if not isinstance(chronicity_branch, BostonChronicityBranch):
        raise TypeError("chronicity_branch must be a BostonChronicityBranch.")

    if signs["ph_7_35"] < 0:
        acid_state = AcidBaseStateCode.ACIDEMIA
    elif signs["ph_7_45"] > 0:
        acid_state = AcidBaseStateCode.ALKALEMIA
    else:
        acid_state = AcidBaseStateCode.NEAR_NORMAL

    pco2_low = signs["paco2_38"] < 0
    pco2_high = signs["paco2_42"] > 0
    hco3_low = signs["hco3_22"] < 0
    hco3_high = signs["hco3_26"] > 0

    if acid_state is AcidBaseStateCode.ACIDEMIA:
        if hco3_low:
            primary = PrimaryProcessCode.METABOLIC_ACIDOSIS
        elif pco2_high:
            primary = PrimaryProcessCode.RESPIRATORY_ACIDOSIS
        else:
            primary = PrimaryProcessCode.ACIDEMIA_UNCLEAR
    elif acid_state is AcidBaseStateCode.ALKALEMIA:
        if hco3_high:
            primary = PrimaryProcessCode.METABOLIC_ALKALOSIS
        elif pco2_low:
            primary = PrimaryProcessCode.RESPIRATORY_ALKALOSIS
        else:
            primary = PrimaryProcessCode.ALKALEMIA_UNCLEAR
    elif pco2_high and hco3_high:
        primary = PrimaryProcessCode.NEAR_NORMAL_RESPIRATORY_ACIDOSIS_OR_MIXED
    elif pco2_low and hco3_low:
        primary = PrimaryProcessCode.NEAR_NORMAL_RESPIRATORY_ALKALOSIS_OR_MIXED
    elif pco2_high or pco2_low or hco3_high or hco3_low:
        primary = PrimaryProcessCode.NEAR_NORMAL_COMPENSATED_OR_MIXED
    else:
        primary = PrimaryProcessCode.NO_CLEAR_PRIMARY_PROCESS

    if primary is PrimaryProcessCode.METABOLIC_ACIDOSIS:
        expected = ExpectedCompensationCode.WINTERS_PACO2_RANGE
        measured, mixed = _comparison_category(
            lower_sign=signs["winters_lower"],
            upper_sign=signs["winters_upper"],
            orientation="measured_minus_expected",
        )
    elif primary is PrimaryProcessCode.METABOLIC_ALKALOSIS:
        expected = ExpectedCompensationCode.METABOLIC_ALKALOSIS_PACO2_RANGE
        measured, mixed = _comparison_category(
            lower_sign=signs["metabolic_alkalosis_lower"],
            upper_sign=signs["metabolic_alkalosis_upper"],
            orientation="measured_minus_expected",
        )
    elif primary in {
        PrimaryProcessCode.RESPIRATORY_ACIDOSIS,
        PrimaryProcessCode.NEAR_NORMAL_RESPIRATORY_ACIDOSIS_OR_MIXED,
    }:
        expected = ExpectedCompensationCode.RESPIRATORY_ACIDOSIS_HCO3_GUIDES
        prefix = (
            "respiratory_acidosis_chronic"
            if chronicity_branch is BostonChronicityBranch.CHRONIC_FLAGGED
            else "respiratory_acidosis_unflagged"
        )
        measured, mixed = _comparison_category(
            lower_sign=signs[f"{prefix}_lower"],
            upper_sign=signs[f"{prefix}_upper"],
            orientation="hco3_minus_expected",
        )
    elif primary in {
        PrimaryProcessCode.RESPIRATORY_ALKALOSIS,
        PrimaryProcessCode.NEAR_NORMAL_RESPIRATORY_ALKALOSIS_OR_MIXED,
    }:
        expected = ExpectedCompensationCode.RESPIRATORY_ALKALOSIS_HCO3_GUIDES
        measured, mixed = _comparison_category(
            lower_sign=signs["respiratory_alkalosis_lower"],
            upper_sign=signs["respiratory_alkalosis_upper"],
            orientation="hco3_minus_expected",
        )
    else:
        expected = ExpectedCompensationCode.NOT_APPLIED
        measured = MeasuredVsExpectedCode.NOT_APPLIED
        mixed = acid_state is AcidBaseStateCode.NEAR_NORMAL and (
            pco2_low or pco2_high or hco3_low or hco3_high
        )

    return BostonClassificationSignature(
        acid_base_state=acid_state,
        primary_process=primary,
        expected_compensation=expected,
        measured_vs_expected=measured,
        mixed_disorder_flag=mixed,
    )
