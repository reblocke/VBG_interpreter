"""Lean regression oracles for the certified Explorer state enumerator.

Dense probes here are deliberately test oracles only.  Production conclusions
come from the terminal-path certificate, never from the number of probes.
"""

from __future__ import annotations

import math
import random
from collections.abc import Iterable

import pytest

from vbg_interpreter.certified_envelope import (
    DECISION_SURFACE_EQUATIONS,
    certify_boston_envelope,
    signature_from_continuous_hh_point,
    signature_from_continuous_measured_values,
)
from vbg_interpreter.models import (
    AcidBaseStateCode,
    ChronicityBranch,
    MeasuredVsExpectedCode,
    PrimaryProcessCode,
)
from vbg_interpreter.state_categories import DECISION_SURFACE_IDS, RuleSignature


def _inclusive_samples(lower: float, upper: float, count: int) -> Iterable[float]:
    step = (upper - lower) / (count - 1)
    return (lower + index * step for index in range(count))


def _certified_by_branch(
    *,
    ph_lower: float,
    ph_upper: float,
    paco2_lower: float,
    paco2_upper: float,
) -> dict[ChronicityBranch, set[RuleSignature]]:
    certified = certify_boston_envelope(
        ph_lower=ph_lower,
        ph_upper=ph_upper,
        paco2_lower=paco2_lower,
        paco2_upper=paco2_upper,
    )
    return {branch.chronicity_branch: set(branch.signatures) for branch in certified.branches}


def _assert_dense_probe_is_contained(
    *,
    ph_lower: float,
    ph_upper: float,
    paco2_lower: float,
    paco2_upper: float,
    count: int,
) -> None:
    certified = _certified_by_branch(
        ph_lower=ph_lower,
        ph_upper=ph_upper,
        paco2_lower=paco2_lower,
        paco2_upper=paco2_upper,
    )
    for branch in ChronicityBranch:
        probed = {
            signature_from_continuous_hh_point(
                ph=ph,
                paco2_mmhg=paco2,
                chronicity_branch=branch,
            )
            for ph in _inclusive_samples(ph_lower, ph_upper, count)
            for paco2 in _inclusive_samples(paco2_lower, paco2_upper, count)
        }
        assert probed <= certified[branch]


def test_decision_surface_catalog_pins_all_executable_boundaries() -> None:
    assert tuple(surface_id for surface_id, _ in DECISION_SURFACE_EQUATIONS) == (
        DECISION_SURFACE_IDS
    )
    assert len(DECISION_SURFACE_EQUATIONS) == 16


@pytest.mark.parametrize(
    ("ph_lower", "ph_upper", "paco2_lower", "paco2_upper"),
    (
        (7.411417434223236, 7.471417434223237, 29.239097948859293, 47.179097948859294),
        (7.30, 7.35, 37.0, 43.0),
        (7.45, 7.55, 37.0, 43.0),
        (7.17, 7.23, 65.0, 90.0),
        (7.52, 7.68, 8.0, 35.0),
    ),
)
def test_dense_display_independent_probe_is_contained_by_each_certified_branch(
    ph_lower: float,
    ph_upper: float,
    paco2_lower: float,
    paco2_upper: float,
) -> None:
    _assert_dense_probe_is_contained(
        ph_lower=ph_lower,
        ph_upper=ph_upper,
        paco2_lower=paco2_lower,
        paco2_upper=paco2_upper,
        count=25,
    )


def test_seeded_threshold_and_tangency_probes_do_not_find_an_omitted_state() -> None:
    generator = random.Random(20260802)
    centers = (
        (7.35, 38.0),
        (7.45, 42.0),
        (6.095 + math.log10(22 / (0.0307 * 40)), 40.0),
        (6.095 + math.log10(26 / (0.0307 * 40)), 40.0),
        (7.411417434223236, 42.021347948859294),
    )
    for center_ph, center_paco2 in centers:
        ph_half_width = generator.uniform(0.001, 0.08)
        paco2_half_width = generator.uniform(0.05, 8.0)
        _assert_dense_probe_is_contained(
            ph_lower=max(6.8, center_ph - ph_half_width),
            ph_upper=min(8.0, center_ph + ph_half_width),
            paco2_lower=max(1.0, center_paco2 - paco2_half_width),
            paco2_upper=center_paco2 + paco2_half_width,
            count=17,
        )


@pytest.mark.parametrize("ph", (7.35, 7.45))
def test_ph_threshold_equalities_remain_near_normal(ph: float) -> None:
    signature = signature_from_continuous_measured_values(
        ph=ph,
        paco2_mmhg=40.0,
        hco3_mmol_l=24.0,
        chronicity_branch=ChronicityBranch.NOT_CHRONIC_FLAGGED,
    )

    assert signature.acid_base_state is AcidBaseStateCode.NEAR_NORMAL


@pytest.mark.parametrize("paco2,hco3", ((38.0, 22.0), (42.0, 26.0)))
def test_paco2_and_hco3_category_threshold_equalities_are_inclusive(
    paco2: float,
    hco3: float,
) -> None:
    signature = signature_from_continuous_measured_values(
        ph=7.40,
        paco2_mmhg=paco2,
        hco3_mmol_l=hco3,
        chronicity_branch=ChronicityBranch.NOT_CHRONIC_FLAGGED,
    )

    assert signature.primary_process is PrimaryProcessCode.NO_CLEAR_PRIMARY_PROCESS


@pytest.mark.parametrize(
    ("paco2", "hco3", "adjusted_field", "expected_below", "expected_above"),
    (
        (
            24.0,
            12.0,
            "paco2",
            MeasuredVsExpectedCode.BELOW_EXPECTED,
            MeasuredVsExpectedCode.WITHIN_EXPECTED,
        ),
        (
            28.0,
            12.0,
            "paco2",
            MeasuredVsExpectedCode.WITHIN_EXPECTED,
            MeasuredVsExpectedCode.ABOVE_EXPECTED,
        ),
        (
            60.0,
            24.0,
            "hco3",
            MeasuredVsExpectedCode.BELOW_EXPECTED,
            MeasuredVsExpectedCode.WITHIN_EXPECTED,
        ),
        (
            60.0,
            34.0,
            "hco3",
            MeasuredVsExpectedCode.WITHIN_EXPECTED,
            MeasuredVsExpectedCode.ABOVE_EXPECTED,
        ),
    ),
)
def test_compensation_limit_equalities_remain_inclusive(
    paco2: float,
    hco3: float,
    adjusted_field: str,
    expected_below: MeasuredVsExpectedCode,
    expected_above: MeasuredVsExpectedCode,
) -> None:
    def classify(paco2_value: float, hco3_value: float) -> MeasuredVsExpectedCode:
        return signature_from_continuous_measured_values(
            ph=7.20,
            paco2_mmhg=paco2_value,
            hco3_mmol_l=hco3_value,
            chronicity_branch=ChronicityBranch.NOT_CHRONIC_FLAGGED,
        ).measured_vs_expected

    assert classify(paco2, hco3) is MeasuredVsExpectedCode.WITHIN_EXPECTED
    if adjusted_field == "paco2":
        below = classify(math.nextafter(paco2, -math.inf), hco3)
        above = classify(math.nextafter(paco2, math.inf), hco3)
    else:
        below = classify(paco2, math.nextafter(hco3, -math.inf))
        above = classify(paco2, math.nextafter(hco3, math.inf))
    assert below is expected_below
    assert above is expected_above
