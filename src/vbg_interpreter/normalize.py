"""Single-boundary unit normalization for explorer inputs."""

from __future__ import annotations

import math

from vbg_interpreter.evidence import MMHG_PER_KPA
from vbg_interpreter.models import (
    CurrentVbg,
    ExplorerInputError,
    NormalizedExplorerInput,
    NormalizedPriorObservation,
    NormalizedVbg,
    Pco2Unit,
    PriorObservation,
    VbgExplorerRequest,
)


def normalize_pco2_to_mmhg(value: float, unit: Pco2Unit) -> float:
    """Normalize a finite positive supplied PCO2 to mmHg exactly once."""

    if not isinstance(unit, Pco2Unit):
        raise ExplorerInputError("pco2 unit must be Pco2Unit.")
    normalized = value if unit is Pco2Unit.MMHG else value * MMHG_PER_KPA
    if not math.isfinite(normalized) or normalized <= 0:
        raise ExplorerInputError("normalized PCO2 must be finite and greater than zero.")
    return normalized


def normalize_current_vbg(value: CurrentVbg) -> NormalizedVbg:
    """Keep source units while adding a distinct canonical PCO2 field."""

    if not isinstance(value, CurrentVbg):
        raise ExplorerInputError("current_vbg must be CurrentVbg.")
    return NormalizedVbg(
        ph=value.ph,
        pco2_input=value.pco2,
        pco2_unit=value.pco2_unit,
        pco2_mmhg=normalize_pco2_to_mmhg(value.pco2, value.pco2_unit),
        hco3_mmol_l=value.hco3_mmol_l,
        hco3_basis=value.hco3_basis,
        base_excess_mmol_l=value.base_excess_mmol_l,
        venous_o2_saturation=value.venous_o2_saturation,
        specimen_type=value.specimen_type,
        draw_site=value.draw_site,
    )


def normalize_prior_observation(value: PriorObservation) -> NormalizedPriorObservation:
    """Normalize an observed prior PCO2 without changing its specimen provenance."""

    if not isinstance(value, PriorObservation):
        raise ExplorerInputError("prior_observation must be PriorObservation.")
    pco2_mmhg = (
        None if value.pco2 is None else normalize_pco2_to_mmhg(value.pco2, value.pco2_unit)  # type: ignore[arg-type]
    )
    return NormalizedPriorObservation(observation=value, pco2_mmhg=pco2_mmhg)


def normalize_request(value: VbgExplorerRequest) -> NormalizedExplorerInput:
    """Normalize request units before any model-dependent calculation."""

    if not isinstance(value, VbgExplorerRequest):
        raise ExplorerInputError("request must be VbgExplorerRequest.")
    prior = (
        None
        if value.prior_observation is None
        else normalize_prior_observation(value.prior_observation)
    )
    return NormalizedExplorerInput(
        current_vbg=normalize_current_vbg(value.current_vbg),
        current_chemistry=value.current_chemistry,
        context=value.context,
        prior_observation=prior,
    )
