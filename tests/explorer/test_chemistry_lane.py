"""Partial and complete chemistry-lane behavior for the Explorer."""

from __future__ import annotations

import pytest

from vbg_interpreter.chemistry import calculate_chemistry_interpretation
from vbg_interpreter.models import (
    ChemistryStatus,
    ChemistryTimeRelationship,
    CurrentChemistry,
    CurrentVbg,
    Hco3Basis,
    LimitationCode,
    Pco2Unit,
    StewartPartitionStatus,
)
from vbg_interpreter.normalize import normalize_current_vbg


def _chemistry(*, albumin: float | None = 40.0) -> CurrentChemistry:
    return CurrentChemistry(
        sodium_mmol_l=140.0,
        chloride_mmol_l=105.0,
        serum_total_co2_mmol_l=24.0,
        albumin_g_l=albumin,
        lactate_mmol_l=2.0,
        relationship_to_vbg=ChemistryTimeRelationship.SAME_CLINICAL_TIMEPOINT,
    )


def _normalized_vbg(*, base_excess: float | None = -2.0):
    return normalize_current_vbg(
        CurrentVbg(
            ph=7.32,
            pco2=55.0,
            pco2_unit=Pco2Unit.MMHG,
            hco3_mmol_l=None,
            hco3_basis=Hco3Basis.UNKNOWN,
            base_excess_mmol_l=base_excess,
        )
    )


def test_missing_albumin_keeps_anion_gap_without_imputing_a_partition() -> None:
    result = calculate_chemistry_interpretation(
        _chemistry(albumin=None),
        current_vbg=_normalized_vbg(),
    )

    assert result.anion_gap_mmol_l == pytest.approx(11.0)
    assert result.corrected_anion_gap_mmol_l is None
    assert result.stewart_partition.status is StewartPartitionStatus.NOT_EVALUABLE
    assert "ALBUMIN_CORRECTION_NOT_EVALUABLE" in {
        code.value for code in result.nonidentifiable_components
    }
    assert "ALBUMIN_REQUIRED_FOR_STEWART_PARTITION" in {
        code.value for code in result.nonidentifiable_components
    }


def test_albumin_correction_overflow_keeps_finite_raw_anion_gap() -> None:
    chemistry = CurrentChemistry(
        sodium_mmol_l=1.0,
        chloride_mmol_l=1.4e308,
        serum_total_co2_mmol_l=1.0e307,
        albumin_g_l=1.4e308,
    )

    result = calculate_chemistry_interpretation(chemistry)

    assert result.status is ChemistryStatus.COMPLETED
    assert result.anion_gap_mmol_l == pytest.approx(-1.5e308)
    assert result.corrected_anion_gap_mmol_l is None
    assert result.anion_gap_metadata is not None
    assert result.corrected_anion_gap_metadata is None
    assert "SERUM_ANION_GAP" in result.identifiable_components
    assert "ALBUMIN_CORRECTED_ANION_GAP" not in result.identifiable_components
    assert LimitationCode.ALBUMIN_CORRECTION_NOT_EVALUABLE in result.limitation_codes
    assert LimitationCode.ALBUMIN_CORRECTION_NOT_EVALUABLE in result.nonidentifiable_components


def test_absent_chemistry_is_explicit_without_blocking_the_gas_lane() -> None:
    result = calculate_chemistry_interpretation(
        CurrentChemistry(),
        current_vbg=_normalized_vbg(),
    )

    assert result.status is ChemistryStatus.NOT_PROVIDED
    assert result.anion_gap_mmol_l is None
    assert result.corrected_anion_gap_mmol_l is None
    assert result.stewart_partition.status is StewartPartitionStatus.NOT_EVALUABLE
    assert LimitationCode.ANION_GAP_NOT_EVALUABLE_MISSING_OPERANDS in result.limitation_codes


@pytest.mark.parametrize(
    "chemistry",
    (
        CurrentChemistry(chloride_mmol_l=105.0, serum_total_co2_mmol_l=24.0),
        CurrentChemistry(sodium_mmol_l=140.0, serum_total_co2_mmol_l=24.0),
        CurrentChemistry(sodium_mmol_l=140.0, chloride_mmol_l=105.0),
    ),
)
def test_each_missing_anion_gap_operand_returns_partial_chemistry(
    chemistry: CurrentChemistry,
) -> None:
    result = calculate_chemistry_interpretation(chemistry, current_vbg=_normalized_vbg())

    assert result.status is ChemistryStatus.PARTIAL
    assert result.anion_gap_mmol_l is None
    assert LimitationCode.ANION_GAP_NOT_EVALUABLE_MISSING_OPERANDS in result.limitation_codes


def test_missing_base_excess_keeps_other_chemistry_but_withholds_residual_ions() -> None:
    result = calculate_chemistry_interpretation(
        _chemistry(),
        current_vbg=_normalized_vbg(base_excess=None),
    )

    assert result.anion_gap_mmol_l == pytest.approx(11.0)
    assert result.corrected_anion_gap_mmol_l == pytest.approx(11.0)
    assert result.stewart_partition.status is StewartPartitionStatus.NOT_EVALUABLE
    assert "BASE_EXCESS_REQUIRED_FOR_STEWART_PARTITION" in {
        code.value for code in result.nonidentifiable_components
    }
    assert "RESIDUAL_UNMEASURED_IONS_NOT_IDENTIFIABLE" in {
        code.value for code in result.nonidentifiable_components
    }


@pytest.mark.parametrize(
    "relationship",
    (
        ChemistryTimeRelationship.DIFFERENT_TIMEPOINT,
        ChemistryTimeRelationship.UNKNOWN,
    ),
)
def test_noncontemporaneous_chemistry_remains_available_with_its_provenance(
    relationship: ChemistryTimeRelationship,
) -> None:
    chemistry = CurrentChemistry(
        sodium_mmol_l=140.0,
        chloride_mmol_l=105.0,
        serum_total_co2_mmol_l=24.0,
        albumin_g_l=40.0,
        relationship_to_vbg=relationship,
    )

    result = calculate_chemistry_interpretation(chemistry, current_vbg=_normalized_vbg())

    assert result.relationship_to_vbg is relationship
    assert result.anion_gap_mmol_l == pytest.approx(11.0)
    assert result.stewart_partition.status is StewartPartitionStatus.NOT_EVALUABLE


def test_complete_partition_uses_specimen_neutral_operands_not_serum_total_co2() -> None:
    result = calculate_chemistry_interpretation(_chemistry(), current_vbg=_normalized_vbg())

    partition = result.stewart_partition
    assert partition.status is StewartPartitionStatus.COMPLETED
    assert partition.basis == "VENOUS_BASIS"
    assert "calculated_hco3_mmol_l" not in partition.to_dict()
    assert "VENOUS_BASIS_STEWART_PARTITION" in result.identifiable_components


def test_stewart_partition_can_complete_without_serum_total_co2() -> None:
    chemistry = CurrentChemistry(
        sodium_mmol_l=140.0,
        chloride_mmol_l=105.0,
        albumin_g_l=40.0,
        lactate_mmol_l=2.0,
        relationship_to_vbg=ChemistryTimeRelationship.SAME_CLINICAL_TIMEPOINT,
    )
    result = calculate_chemistry_interpretation(chemistry, current_vbg=_normalized_vbg())

    assert result.status is ChemistryStatus.PARTIAL
    assert result.anion_gap_mmol_l is None
    assert result.stewart_partition.status is StewartPartitionStatus.COMPLETED


def test_stewart_partition_does_not_promote_a_henderson_hasselbalch_derived_ph() -> None:
    derived_ph_vbg = normalize_current_vbg(
        CurrentVbg(
            pco2=55.0,
            pco2_unit=Pco2Unit.MMHG,
            hco3_mmol_l=27.0,
            hco3_basis=Hco3Basis.REPORTED,
            base_excess_mmol_l=-2.0,
        )
    )

    result = calculate_chemistry_interpretation(
        _chemistry(),
        current_vbg=derived_ph_vbg,
    )

    assert result.stewart_partition.status is StewartPartitionStatus.NOT_EVALUABLE


def test_completed_partition_passes_only_specimen_neutral_operands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import stewartlight

    original = stewartlight.calculate_stewart_partition
    captured = []

    def capture_partition_input(input_data):
        captured.append(input_data)
        return original(input_data)

    monkeypatch.setattr(stewartlight, "calculate_stewart_partition", capture_partition_input)
    calculate_chemistry_interpretation(_chemistry(), current_vbg=_normalized_vbg())

    assert len(captured) == 1
    assert set(captured[0].to_dict()) == {
        "ph",
        "sbe_mmol_l",
        "na_mmol_l",
        "cl_mmol_l",
        "albumin_g_l",
        "lactate_mmol_l",
    }


def test_stewart_numerical_domain_refusal_keeps_basic_chemistry_available() -> None:
    overflowing_vbg = normalize_current_vbg(
        CurrentVbg(
            ph=7.32,
            pco2=55.0,
            pco2_unit=Pco2Unit.MMHG,
            hco3_mmol_l=None,
            hco3_basis=Hco3Basis.UNKNOWN,
            base_excess_mmol_l=-1e308,
        )
    )
    overflowing_chemistry = CurrentChemistry(
        sodium_mmol_l=1e308,
        chloride_mmol_l=1.0,
        serum_total_co2_mmol_l=24.0,
        albumin_g_l=40.0,
        relationship_to_vbg=ChemistryTimeRelationship.SAME_CLINICAL_TIMEPOINT,
    )

    result = calculate_chemistry_interpretation(
        overflowing_chemistry,
        current_vbg=overflowing_vbg,
    )

    assert result.anion_gap_mmol_l == pytest.approx(1e308)
    assert result.stewart_partition.status is StewartPartitionStatus.MODEL_DOMAIN_REFUSAL
    assert LimitationCode.STEWART_PARTITION_NUMERICAL_DOMAIN_REFUSAL in {
        *result.limitation_codes,
        *result.stewart_partition.limitation_codes,
    }
