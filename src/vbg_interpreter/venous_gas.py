"""Completion and descriptive orientation of a current venous gas.

This module completes only the algebraic pH--PCO2--HCO3 relationship.  It does
not arterialize a venous value or apply the Boston ruleset to venous inputs.
"""

from __future__ import annotations

import math

from vbg_interpreter.models import (
    CompletedVenousGas,
    ExplorerInputError,
    GasValueOrigin,
    LimitationCode,
    NormalizedVbg,
    VenousOrientation,
    VenousOrientationCode,
)

HENDERSON_HASSELBALCH_CO2_SOLUBILITY = 0.0307
HENDERSON_HASSELBALCH_PKA = 6.095
HCO3_DISCORDANCE_WARNING_MMOL_L = 0.5


def hco3_from_ph_pco2(*, ph: float, pco2_mmhg: float) -> float:
    """Return the derived blood-gas HCO3 from a positive pH--PCO2 coordinate."""

    try:
        return (
            HENDERSON_HASSELBALCH_CO2_SOLUBILITY
            * pco2_mmhg
            * (10 ** (ph - HENDERSON_HASSELBALCH_PKA))
        )
    except OverflowError as error:
        raise ExplorerInputError("Venous-gas HCO3 completion overflowed.") from error


def pco2_from_ph_hco3(*, ph: float, hco3_mmol_l: float) -> float:
    """Return a derived PCO2 in mmHg from positive pH and blood-gas HCO3."""

    try:
        return hco3_mmol_l / (
            HENDERSON_HASSELBALCH_CO2_SOLUBILITY * (10 ** (ph - HENDERSON_HASSELBALCH_PKA))
        )
    except OverflowError as error:
        raise ExplorerInputError("Venous-gas PCO2 completion overflowed.") from error


def ph_from_pco2_hco3(*, pco2_mmhg: float, hco3_mmol_l: float) -> float:
    """Return a derived pH from positive PCO2 and blood-gas HCO3."""

    try:
        return HENDERSON_HASSELBALCH_PKA + math.log10(
            hco3_mmol_l / (HENDERSON_HASSELBALCH_CO2_SOLUBILITY * pco2_mmhg)
        )
    except (OverflowError, ValueError, ZeroDivisionError) as error:
        raise ExplorerInputError(
            "Venous-gas pH completion was outside the numerical domain."
        ) from error


def complete_venous_gas(value: NormalizedVbg) -> CompletedVenousGas:
    """Complete exactly one missing gas coordinate from the other two when needed."""

    if not isinstance(value, NormalizedVbg):
        raise TypeError("value must be NormalizedVbg.")

    ph = value.ph
    pco2 = value.pco2_mmhg
    hco3 = value.hco3_mmol_l
    supplied = {
        "ph": ph is not None,
        "pco2": pco2 is not None,
        "hco3": hco3 is not None,
    }
    if sum(supplied.values()) < 2:  # defensive: CurrentVbg validates this at the boundary
        raise ExplorerInputError("At least two venous gas values are required for completion.")

    if ph is None:
        if pco2 is None or hco3 is None:  # pragma: no cover - guarded above
            raise AssertionError("pH completion requires PCO2 and HCO3.")
        ph = ph_from_pco2_hco3(pco2_mmhg=pco2, hco3_mmol_l=hco3)
    if pco2 is None:
        if ph is None or hco3 is None:  # pragma: no cover - guarded above
            raise AssertionError("PCO2 completion requires pH and HCO3.")
        pco2 = pco2_from_ph_hco3(ph=ph, hco3_mmol_l=hco3)
    if hco3 is None:
        if ph is None or pco2 is None:  # pragma: no cover - guarded above
            raise AssertionError("HCO3 completion requires pH and PCO2.")
        hco3 = hco3_from_ph_pco2(ph=ph, pco2_mmhg=pco2)

    values = (ph, pco2, hco3)
    if not all(math.isfinite(item) and item > 0 for item in values):
        raise ExplorerInputError("Venous-gas completion yielded a nonpositive or nonfinite value.")

    comparator = None
    discrepancy = None
    limitations: tuple[LimitationCode, ...] = ()
    if all(supplied.values()):
        comparator = hco3_from_ph_pco2(ph=ph, pco2_mmhg=pco2)
        discrepancy = hco3 - comparator
        if abs(discrepancy) > HCO3_DISCORDANCE_WARNING_MMOL_L:
            limitations = (LimitationCode.HCO3_INPUT_DISCORDANT_WITH_PH_PCO2,)

    return CompletedVenousGas(
        ph=ph,
        pco2_mmhg=pco2,
        hco3_mmol_l=hco3,
        ph_origin=(
            GasValueOrigin.SUPPLIED
            if supplied["ph"]
            else GasValueOrigin.DERIVED_HENDERSON_HASSELBALCH
        ),
        pco2_origin=(
            GasValueOrigin.SUPPLIED
            if supplied["pco2"]
            else GasValueOrigin.DERIVED_HENDERSON_HASSELBALCH
        ),
        hco3_origin=(
            GasValueOrigin.SUPPLIED
            if supplied["hco3"]
            else GasValueOrigin.DERIVED_HENDERSON_HASSELBALCH
        ),
        hco3_ph_pco2_comparator_mmol_l=comparator,
        hco3_discrepancy_mmol_l=discrepancy,
        limitation_codes=limitations,
    )


def describe_venous_orientation(value: CompletedVenousGas) -> VenousOrientation:
    """Return only a descriptive pH location relative to retained ruleset bands."""

    if not isinstance(value, CompletedVenousGas):
        raise TypeError("value must be CompletedVenousGas.")
    if value.ph < 7.35:
        orientation = VenousOrientationCode.BELOW_RULESET_REFERENCE_BAND
    elif value.ph > 7.45:
        orientation = VenousOrientationCode.ABOVE_RULESET_REFERENCE_BAND
    else:
        orientation = VenousOrientationCode.WITHIN_RULESET_REFERENCE_BAND
    return VenousOrientation(ph_reference_orientation=orientation)
