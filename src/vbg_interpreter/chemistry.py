"""Independent serum calculations and a provenance-preserving venous Stewart adapter."""

from vbg_interpreter.evidence import calculation
from vbg_interpreter.models import (
    Calculation,
    CalculationStatus,
    ChemistryTimeRelationship,
    VbgExplorerRequest,
    VenousGas,
)


def calculate_chemistry(request: VbgExplorerRequest, gas: VenousGas) -> dict[str, Calculation]:
    chem = request.current_chemistry
    na, cl, co2, alb = (
        chem.sodium_mmol_l,
        chem.chloride_mmol_l,
        chem.serum_total_co2_mmol_l,
        chem.albumin_g_l,
    )
    operands = {"sodium": na, "chloride": cl, "serum total CO2": co2}
    missing = tuple(k for k, v in operands.items() if v is None)
    origins = {k: "MEASURED_OR_REPORTED_SERUM" for k, v in operands.items() if v is not None}
    ag = None if missing else na - cl - co2
    gap = calculation(
        "serum_anion_gap_v1",
        values={} if ag is None else {"anion_gap": ag},
        units={"anion_gap": "mmol/L"},
        origins=origins,
        missing=missing,
        limitations=(
            "Serum total CO2 is distinct from blood-gas HCO3; reference intervals are "
            "laboratory-dependent.",
        ),
    )
    correction_missing = (*missing, *(("albumin",) if alb is None else ()))
    corrected = None if correction_missing else ag + 0.25 * (40 - alb)
    correction = calculation(
        "albumin_corrected_anion_gap_v1",
        values={} if corrected is None else {"corrected_anion_gap": corrected},
        units={"corrected_anion_gap": "mmol/L"},
        origins={
            **origins,
            **({"albumin": "MEASURED_OR_REPORTED_SERUM"} if alb is not None else {}),
        },
        missing=correction_missing,
        limitations=("No universal high/normal/low AG cutoff is applied.",),
    )
    difference = calculation(
        "sodium_chloride_difference_v1",
        values={} if na is None or cl is None else {"sodium_chloride_difference": na - cl},
        units={"sodium_chloride_difference": "mmol/L"},
        origins={k: origins[k] for k in ("sodium", "chloride") if k in origins},
        missing=tuple(k for k, v in (("sodium", na), ("chloride", cl)) if v is None),
        limitations=("Descriptive strong-ion surrogate; not a complete metabolic interpretation.",),
    )
    return {
        "anion_gap": gap,
        "corrected_anion_gap": correction,
        "sodium_chloride_difference": difference,
        "venous_stewart_partition": _partition(request, gas),
    }


def _partition(request: VbgExplorerRequest, gas: VenousGas) -> Calculation:
    from stewartlight import StewartPartitionInput, calculate_stewart_partition

    chem, source, sbe = request.current_chemistry, request.current_vbg, gas.standard_base_excess
    operands = {
        "measured venous pH": source.ph,
        "sodium": chem.sodium_mmol_l,
        "chloride": chem.chloride_mmol_l,
        "albumin": chem.albumin_g_l,
    }
    missing = [k for k, v in operands.items() if v is None]
    if sbe.status is CalculationStatus.UNAVAILABLE_MISSING_INPUT:
        missing.append("reported or calculable venous standard base excess")
    if chem.relationship_to_vbg is ChemistryTimeRelationship.UNKNOWN:
        missing.append("same clinical timepoint confirmation")
    outside = ()
    if chem.relationship_to_vbg is ChemistryTimeRelationship.DIFFERENT_TIMEPOINT:
        outside = ("Chemistry is from a different timepoint.",)
    origins = {k: "MEASURED_OR_REPORTED" for k, v in operands.items() if v is not None}
    if sbe.status is CalculationStatus.AVAILABLE:
        origins["sbe"] = sbe.output_provenance
        origins.update({"sbe." + k: v for k, v in sbe.input_origins.items()})
    if chem.lactate_mmol_l is not None:
        origins["lactate"] = "MEASURED_OR_REPORTED_SERUM"
    limits = ("Venous-basis partition of reported or calculated SBE; not arterial SBE.",)
    if sbe.output_provenance == "CALCULATED_VAN_SLYKE":
        limits += sbe.limitations
    kwargs = dict(origins=origins, limitations=limits, provenance="VENOUS_BASIS_PARTITION")
    method = "stewartlight_venous_partition_v1"
    if missing or outside:
        return calculation(method, missing=tuple(missing), outside=outside, **kwargs)
    if sbe.status is CalculationStatus.MODEL_DOMAIN_REFUSAL:
        return calculation(method, domain_refusal=True, **kwargs)
    try:
        partition = calculate_stewart_partition(
            StewartPartitionInput(
                ph=source.ph,
                sbe_mmol_l=sbe.values["sbe"],
                na_mmol_l=chem.sodium_mmol_l,
                cl_mmol_l=chem.chloride_mmol_l,
                albumin_g_l=chem.albumin_g_l,
                lactate_mmol_l=chem.lactate_mmol_l,
            )
        )
        values = {
            "total_sbe": partition.sbe_total,
            "sodium_chloride_component": partition.sbe_sid,
            "albumin_component": partition.sbe_alb,
            "unmeasured_ions_component": partition.sbe_ui,
            "reconstructed_sbe": partition.reconstructed_sbe,
            "closure_error": partition.closure_error,
        }
        if partition.lactate is not None:
            values.update(
                lactate_component=partition.lactate.sbe_lactate,
                nonlactate_unmeasured_component=partition.lactate.sbe_ui_non_lactate,
            )
        return calculation(method, values=values, units={k: "mmol/L" for k in values}, **kwargs)
    except (ArithmeticError, ValueError):
        return calculation(method, domain_refusal=True, **kwargs)
