"""Explicit-unit conversion, without completing or arterializing source measurements."""

import math

from vbg_interpreter.evidence import MMHG_PER_KPA
from vbg_interpreter.models import ExplorerInputError, Pco2Unit


def normalize_pco2_to_mmhg(value: float, unit: Pco2Unit) -> float:
    if not isinstance(unit, Pco2Unit):
        raise ExplorerInputError("PCO2 needs an explicit unit.")
    result = value if unit is Pco2Unit.MMHG else value * MMHG_PER_KPA
    if not math.isfinite(result) or result <= 0:
        raise ExplorerInputError("PCO2 conversion is outside the numerical domain.")
    return result
