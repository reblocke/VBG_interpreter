"""Progressive serum-chemistry context and venous-basis Stewart partitioning."""

from __future__ import annotations

import math

from vbg_interpreter.evidence import (
    ALBUMIN_CORRECTED_ANION_GAP_METADATA,
    SERUM_ANION_GAP_METADATA,
    VENOUS_STEWART_PARTITION_METADATA,
)
from vbg_interpreter.models import (
    ChemistryInterpretation,
    ChemistryStatus,
    ChemistryTimeRelationship,
    CurrentChemistry,
    LimitationCode,
    NormalizedVbg,
    StewartPartitionContext,
    StewartPartitionStatus,
)

ALBUMIN_ANION_GAP_CORRECTION_PER_G_L = 0.25
ALBUMIN_REFERENCE_G_L = 40.0


def calculate_chemistry_interpretation(
    value: CurrentChemistry,
    *,
    current_vbg: NormalizedVbg | None = None,
) -> ChemistryInterpretation:
    """Return every chemistry fact whose explicit operands are present.

    Serum total CO2 remains chemistry-only.  It never fills blood-gas HCO3 or
    contributes to current PCO2.  An incomplete chemistry panel withholds only
    its dependent calculation rather than the complete Explorer result.
    """

    if not isinstance(value, CurrentChemistry):
        raise TypeError("value must be CurrentChemistry.")

    has_any = any(
        item is not None
        for item in (
            value.sodium_mmol_l,
            value.chloride_mmol_l,
            value.serum_total_co2_mmol_l,
            value.albumin_g_l,
            value.lactate_mmol_l,
        )
    )
    ag_ready = all(
        item is not None
        for item in (value.sodium_mmol_l, value.chloride_mmol_l, value.serum_total_co2_mmol_l)
    )
    anion_gap = None
    identifiable: list[str] = []
    limitations: list[LimitationCode] = [
        LimitationCode.SERUM_TOTAL_CO2_IS_NOT_BLOOD_GAS_HCO3,
        LimitationCode.NO_CURRENT_PACO2_FROM_CHEMISTRY_ONLY,
    ]
    if ag_ready:
        if (
            value.sodium_mmol_l is None
            or value.chloride_mmol_l is None
            or value.serum_total_co2_mmol_l is None
        ):  # pragma: no cover - guarded by ag_ready
            raise AssertionError("Anion-gap operands must be present.")
        anion_gap = value.sodium_mmol_l - value.chloride_mmol_l - value.serum_total_co2_mmol_l
        identifiable.append("SERUM_ANION_GAP")
    else:
        limitations.append(LimitationCode.ANION_GAP_NOT_EVALUABLE_MISSING_OPERANDS)

    corrected = None
    if anion_gap is not None and value.albumin_g_l is not None:
        corrected_candidate = anion_gap + ALBUMIN_ANION_GAP_CORRECTION_PER_G_L * (
            ALBUMIN_REFERENCE_G_L - value.albumin_g_l
        )
        if math.isfinite(corrected_candidate):
            corrected = corrected_candidate
            identifiable.append("ALBUMIN_CORRECTED_ANION_GAP")
        else:
            limitations.append(LimitationCode.ALBUMIN_CORRECTION_NOT_EVALUABLE)
    else:
        limitations.append(LimitationCode.ALBUMIN_CORRECTION_NOT_EVALUABLE)

    partition = _calculate_stewart_partition(value, current_vbg=current_vbg)
    if partition.status is StewartPartitionStatus.COMPLETED:
        identifiable.append("VENOUS_BASIS_STEWART_PARTITION")
    else:
        limitations.extend(partition.limitation_codes)

    if not has_any:
        status = ChemistryStatus.NOT_PROVIDED
    elif ag_ready:
        status = ChemistryStatus.COMPLETED
    else:
        status = ChemistryStatus.PARTIAL
    limitation_tuple = _unique_limitations(limitations)
    return ChemistryInterpretation(
        status=status,
        relationship_to_vbg=value.relationship_to_vbg,
        sodium_mmol_l=value.sodium_mmol_l,
        chloride_mmol_l=value.chloride_mmol_l,
        serum_total_co2_mmol_l=value.serum_total_co2_mmol_l,
        albumin_g_l=value.albumin_g_l,
        lactate_mmol_l=value.lactate_mmol_l,
        anion_gap_mmol_l=anion_gap,
        corrected_anion_gap_mmol_l=corrected,
        limitation_codes=limitation_tuple,
        stewart_partition=partition,
        identifiable_components=tuple(identifiable),
        nonidentifiable_components=tuple(
            code
            for code in limitation_tuple
            if code
            in {
                LimitationCode.ANION_GAP_NOT_EVALUABLE_MISSING_OPERANDS,
                LimitationCode.ALBUMIN_CORRECTION_NOT_EVALUABLE,
                LimitationCode.STEWART_PARTITION_NOT_EVALUABLE,
                LimitationCode.BASE_EXCESS_REQUIRED_FOR_STEWART_PARTITION,
                LimitationCode.ALBUMIN_REQUIRED_FOR_STEWART_PARTITION,
                LimitationCode.CHEMISTRY_TIME_RELATIONSHIP_NOT_SAME,
                LimitationCode.STEWART_PARTITION_NUMERICAL_DOMAIN_REFUSAL,
                LimitationCode.RESIDUAL_UNMEASURED_IONS_NOT_IDENTIFIABLE,
            }
        ),
        anion_gap_metadata=SERUM_ANION_GAP_METADATA if anion_gap is not None else None,
        corrected_anion_gap_metadata=(
            ALBUMIN_CORRECTED_ANION_GAP_METADATA if corrected is not None else None
        ),
    )


def _calculate_stewart_partition(
    chemistry: CurrentChemistry,
    *,
    current_vbg: NormalizedVbg | None,
) -> StewartPartitionContext:
    reasons: list[LimitationCode] = []
    if current_vbg is None or current_vbg.ph is None:
        reasons.append(LimitationCode.STEWART_PARTITION_NOT_EVALUABLE)
    elif current_vbg.base_excess_mmol_l is None:
        reasons.extend(
            (
                LimitationCode.STEWART_PARTITION_NOT_EVALUABLE,
                LimitationCode.BASE_EXCESS_REQUIRED_FOR_STEWART_PARTITION,
            )
        )
    if chemistry.sodium_mmol_l is None or chemistry.chloride_mmol_l is None:
        reasons.append(LimitationCode.STEWART_PARTITION_NOT_EVALUABLE)
    if chemistry.albumin_g_l is None:
        reasons.extend(
            (
                LimitationCode.STEWART_PARTITION_NOT_EVALUABLE,
                LimitationCode.ALBUMIN_REQUIRED_FOR_STEWART_PARTITION,
            )
        )
    if chemistry.relationship_to_vbg is not ChemistryTimeRelationship.SAME_CLINICAL_TIMEPOINT:
        reasons.extend(
            (
                LimitationCode.STEWART_PARTITION_NOT_EVALUABLE,
                LimitationCode.CHEMISTRY_TIME_RELATIONSHIP_NOT_SAME,
            )
        )
    if reasons:
        return StewartPartitionContext.not_evaluable(
            *_unique_limitations(
                (*reasons, LimitationCode.RESIDUAL_UNMEASURED_IONS_NOT_IDENTIFIABLE)
            )
        )
    if (
        current_vbg is None
        or current_vbg.ph is None
        or current_vbg.base_excess_mmol_l is None
        or chemistry.sodium_mmol_l is None
        or chemistry.chloride_mmol_l is None
        or chemistry.albumin_g_l is None
    ):
        raise AssertionError("Eligible partition inputs must be complete.")

    from stewartlight import StewartPartitionInput, calculate_stewart_partition

    try:
        upstream_partition = calculate_stewart_partition(
            StewartPartitionInput(
                ph=current_vbg.ph,
                sbe_mmol_l=current_vbg.base_excess_mmol_l,
                na_mmol_l=chemistry.sodium_mmol_l,
                cl_mmol_l=chemistry.chloride_mmol_l,
                albumin_g_l=chemistry.albumin_g_l,
                lactate_mmol_l=chemistry.lactate_mmol_l,
            )
        )
        lactate = upstream_partition.lactate
        return StewartPartitionContext(
            status=StewartPartitionStatus.COMPLETED,
            basis="VENOUS_BASIS",
            sbe_total_mmol_l=upstream_partition.sbe_total,
            sid_reference_mmol_l=upstream_partition.sid_reference,
            sid_reference_adjusted=upstream_partition.sid_reference_adjusted,
            sbe_sid_mmol_l=upstream_partition.sbe_sid,
            sbe_albumin_mmol_l=upstream_partition.sbe_alb,
            sbe_unmeasured_ions_mmol_l=upstream_partition.sbe_ui,
            lactate_sbe_mmol_l=None if lactate is None else lactate.sbe_lactate,
            nonlactate_unmeasured_ions_sbe_mmol_l=(
                None if lactate is None else lactate.sbe_ui_non_lactate
            ),
            reconstructed_sbe_mmol_l=upstream_partition.reconstructed_sbe,
            closure_error_mmol_l=upstream_partition.closure_error,
            offsetting_components_present=upstream_partition.offsetting_components_present,
            partition_metadata=VENOUS_STEWART_PARTITION_METADATA,
        )
    except (OverflowError, ValueError):
        return StewartPartitionContext.model_domain_refusal(
            LimitationCode.STEWART_PARTITION_NOT_EVALUABLE,
            LimitationCode.STEWART_PARTITION_NUMERICAL_DOMAIN_REFUSAL,
            LimitationCode.RESIDUAL_UNMEASURED_IONS_NOT_IDENTIFIABLE,
        )


def _unique_limitations(
    values: tuple[LimitationCode, ...] | list[LimitationCode],
) -> tuple[LimitationCode, ...]:
    return tuple(dict.fromkeys(values))
