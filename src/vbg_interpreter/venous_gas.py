"""Partial venous gas completion and normothermic venous-basis SBE."""

from __future__ import annotations

import math

from vbg_interpreter.evidence import calculation
from vbg_interpreter.models import (
    BaseExcessBasis,
    Calculation,
    CalculationStatus,
    CurrentVbg,
    GasValueOrigin,
    VenousGas,
)
from vbg_interpreter.normalize import normalize_pco2_to_mmhg

HH = "henderson_hasselbalch_v1"
SBE = "venous_sbe_van_slyke_37c_v1"
SUPPLIED = GasValueOrigin.MEASURED_OR_REPORTED.value
DERIVED = GasValueOrigin.CALCULATED_HENDERSON_HASSELBALCH.value
UNITS = {"ph": "pH units", "pco2": "mmHg", "hco3": "mmol/L"}
SBE_LIMITS = (
    "Calculated venous-basis SBE; normothermia (37°C) assumed.",
    "Standardized effective hemoglobin 5 g/dL; no analyzer-equivalence claim.",
)


def hco3_from_ph_pco2(*, ph: float, pco2_mmhg: float) -> float:
    return 0.0307 * pco2_mmhg * 10 ** (ph - 6.095)


def pco2_from_ph_hco3(*, ph: float, hco3_mmol_l: float) -> float:
    return hco3_mmol_l / (0.0307 * 10 ** (ph - 6.095))


def ph_from_pco2_hco3(*, pco2_mmhg: float, hco3_mmol_l: float) -> float:
    return 6.095 + math.log10(hco3_mmol_l / (0.0307 * pco2_mmhg))


def sbe_from_ph_hco3(*, ph: float, hco3_mmol_l: float) -> float:
    """Selected standardized Van Slyke equation; output remains venous basis."""
    return 0.9287 * (hco3_mmol_l - 24.4 + 14.83 * (ph - 7.4))


def complete_venous_gas(source: CurrentVbg) -> VenousGas:
    measured: dict[str, object] = {}
    for key, value, unit, basis in (
        ("ph", source.ph, "pH units", SUPPLIED),
        ("pco2", source.pco2, source.pco2_unit, SUPPLIED),
        ("hco3", source.hco3_mmol_l, "mmol/L", source.hco3_basis.value),
        ("base_excess", source.base_excess_mmol_l, "mmol/L", source.base_excess_basis.value),
    ):
        if value is not None:
            measured[key] = {"value": value, "units": unit, "provenance": SUPPLIED, "basis": basis}
    if source.venous_o2_saturation is not None:
        sat = source.venous_o2_saturation
        measured["venous_saturation"] = {
            "value": sat.value,
            "units": sat.unit.value,
            "provenance": SUPPLIED,
        }
    values = {"ph": source.ph, "pco2": source.pco2, "hco3": source.hco3_mmol_l}
    origins = {key: SUPPLIED for key, value in values.items() if value is not None}
    if source.hco3_mmol_l is not None:
        origins["hco3_basis"] = source.hco3_basis.value
    calculated = {}
    normalization_failed = False
    if source.pco2 is not None:
        try:
            values["pco2"] = normalize_pco2_to_mmhg(source.pco2, source.pco2_unit)
            measured["pco2"]["normalized_mmhg"] = values["pco2"]
        except ValueError:
            normalization_failed = True
    original = values.copy()
    for key in values:
        if original[key] is not None:
            continue
        operands = {k: v for k, v in original.items() if k != key}
        missing = tuple(k for k, v in operands.items() if v is None)
        result = None
        failed = normalization_failed
        if not missing and not failed:
            try:
                if key == "ph":
                    result = ph_from_pco2_hco3(pco2_mmhg=values["pco2"], hco3_mmol_l=values["hco3"])
                elif key == "pco2":
                    result = pco2_from_ph_hco3(ph=values["ph"], hco3_mmol_l=values["hco3"])
                else:
                    result = hco3_from_ph_pco2(ph=values["ph"], pco2_mmhg=values["pco2"])
                failed = not math.isfinite(result) or result <= 0
            except (ArithmeticError, ValueError):
                failed = True
        calculated[key] = calculation(
            HH,
            values={} if result is None else {key: result},
            units={key: UNITS[key]},
            origins={k: origins[k] for k in (*operands, "hco3_basis") if k in origins},
            provenance=DERIVED,
            missing=missing,
            domain_refusal=failed,
            limitations=("Algebraic venous coordinate; not an independent measurement.",),
        )
        if calculated[key].status is CalculationStatus.AVAILABLE:
            values[key] = result
            origins[key] = DERIVED
    comparator = None
    comparator_failed = normalization_failed
    if source.ph is not None and source.pco2 is not None and not normalization_failed:
        try:
            comparator = hco3_from_ph_pco2(ph=source.ph, pco2_mmhg=values["pco2"])
            comparator_failed = not math.isfinite(comparator) or comparator <= 0
        except (ArithmeticError, ValueError):
            comparator_failed = True
    consistency_values = {}
    if comparator is not None and source.hco3_mmol_l is not None:
        consistency_values = {
            "reported_hco3": source.hco3_mmol_l,
            "hh_hco3": comparator,
            "reported_minus_hh": source.hco3_mmol_l - comparator,
        }
    consistency = calculation(
        HH,
        values=consistency_values,
        units={key: "mmol/L" for key in consistency_values},
        origins={k: SUPPLIED for k, v in original.items() if v is not None},
        missing=tuple(k for k, v in original.items() if v is None),
        domain_refusal=comparator_failed,
        limitations=("Numerical comparison only; discrepancy is not a clinical disorder.",),
    )
    sbe = _standard_base_excess(source, values, origins, comparator, comparator_failed)
    position = None
    if source.ph is not None:
        position = "below" if source.ph < 7.35 else "above" if source.ph > 7.45 else "within"
    return VenousGas(measured, calculated, consistency, position, sbe)


def _standard_base_excess(
    source: CurrentVbg,
    values: dict,
    origins: dict,
    comparator: float | None,
    comparator_failed: bool,
) -> Calculation:
    if (
        source.base_excess_mmol_l is not None
        and source.base_excess_basis is BaseExcessBasis.STANDARD
    ):
        return calculation(
            "reported_venous_sbe_v1",
            values={"sbe": source.base_excess_mmol_l},
            units={"sbe": "mmol/L"},
            origins={"base_excess": SUPPLIED},
            provenance=SUPPLIED,
            limitations=("Reported venous standard base excess; remains venous.",),
        )
    ph, hco3 = values["ph"], values["hco3"]
    input_origins = {k: origins[k] for k in ("ph", "hco3", "hco3_basis") if k in origins}
    if origins.get("ph") == DERIVED:
        input_origins["pco2"] = SUPPLIED
    # A measured pH/PCO2 pair takes precedence over an inconsistent third coordinate.
    if source.ph is not None and source.pco2 is not None:
        hco3 = comparator
        input_origins = {"ph": SUPPLIED, "pco2": SUPPLIED, "hco3": DERIVED}
        if comparator_failed:
            return calculation(
                SBE, domain_refusal=True, origins=input_origins, limitations=SBE_LIMITS
            )
    missing = tuple(k for k, v in (("ph", ph), ("hco3", hco3)) if v is None)
    result = None
    if not missing:
        result = sbe_from_ph_hco3(ph=ph, hco3_mmol_l=hco3)
    return calculation(
        SBE,
        values={} if result is None else {"sbe": result},
        units={"sbe": "mmol/L"},
        origins=input_origins,
        provenance=GasValueOrigin.CALCULATED_VAN_SLYKE.value,
        missing=missing,
        limitations=SBE_LIMITS,
    )
