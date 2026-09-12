"""Provisional gas-only assessment; no invented chemistry, BE or chronicity input."""

import math
from dataclasses import dataclass

from stewartlight.interpret import assess_boston

from vbg_interpreter.evidence import calculation
from vbg_interpreter.models import Calculation, CalculationStatus, ProvisionalInterpretation
from vbg_interpreter.serialization import to_primitive
from vbg_interpreter.venous_gas import hco3_from_ph_pco2


@dataclass(frozen=True)
class _EstimatedGas:
    """Structural adapter for the four attributes read by the pinned Boston helper.

    No AcidBaseInput is constructed: its required chemistry and SBE do not apply here.
    False disables the upstream chronic-only branch; it does not assert an acute process.
    """

    ph: float
    pco2_mmhg: float
    hco3_mmol_l: float
    suspect_chronic_hypercapnia: bool = False


def modeled_hco3(ph: Calculation, co2: Calculation) -> Calculation:
    missing = tuple(
        k
        for k, c in (("estimated arterial pH", ph), ("estimated PaCO2", co2))
        if c.status is CalculationStatus.UNAVAILABLE_MISSING_INPUT
    )
    refused = any(c.status is CalculationStatus.MODEL_DOMAIN_REFUSAL for c in (ph, co2))
    kwargs = dict(
        origins={"ph": ph.output_provenance, "pco2": co2.output_provenance},
        provenance="CALCULATED_FROM_ARTERIAL_ESTIMATES",
        limitations=(
            "Modeled arterial bicarbonate from the estimated pair; not "
            "measured or venous bicarbonate.",
        ),
        missing=missing,
        domain_refusal=refused,
    )
    if missing or refused:
        return calculation("modeled_arterial_hh_v1", **kwargs)
    try:
        value = hco3_from_ph_pco2(ph=ph.values["ph"], pco2_mmhg=co2.values["point"])
        kwargs["domain_refusal"] = value <= 0
        return calculation(
            "modeled_arterial_hh_v1",
            values={"modeled_hco3": value},
            units={"modeled_hco3": "mmol/L"},
            **kwargs,
        )
    except (ArithmeticError, ValueError):
        kwargs["domain_refusal"] = True
        return calculation("modeled_arterial_hh_v1", **kwargs)


def _estimated_wording(value):
    if isinstance(value, dict):
        return {k: _estimated_wording(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_estimated_wording(v) for v in value]
    if isinstance(value, str):
        return value.replace("measured", "modeled").replace("likely", "suggested by this estimate")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Nonfinite compensation result")
    return value


def assess_estimated_gas(
    ph: Calculation, co2: Calculation, hco3: Calculation
) -> ProvisionalInterpretation:
    limits = (
        "Provisional interpretation of estimated coordinates; other "
        "acid–base processes are not excluded.",
        "A single gas does not establish chronicity; acute and chronic "
        "comparisons are contextual only.",
    )
    if hco3.status is not CalculationStatus.AVAILABLE:
        return ProvisionalInterpretation(
            hco3.status, missing_inputs=hco3.missing_inputs, limitations=limits
        )
    try:
        gas = _EstimatedGas(ph.values["ph"], co2.values["point"], hco3.values["modeled_hco3"])
        # The pinned helper is duck-typed; tests compare this adapter with its full input.
        assessment = _estimated_wording(to_primitive(assess_boston(gas)))
        assessment["modeled_vs_expected"] = assessment.pop("measured_vs_expected")
        return ProvisionalInterpretation(
            CalculationStatus.AVAILABLE, assessment=assessment, limitations=limits
        )
    except (ArithmeticError, ValueError):
        return ProvisionalInterpretation(CalculationStatus.MODEL_DOMAIN_REFUSAL, limitations=limits)
