"""Small deterministic, synthetic scientific acceptance matrix for the Explorer."""

from __future__ import annotations

from dataclasses import replace

import pytest

from vbg_interpreter.interpret import interpret_vbg
from vbg_interpreter.models import (
    CandidateRegionStatus,
    ChemistryTimeRelationship,
    CurrentChemistry,
    CurrentVbg,
    DrawSite,
    ExplorerContext,
    LimitationCode,
    Pco2Unit,
    PriorObservation,
    PriorObservationType,
    SaturationInput,
    SaturationUnit,
    SpecimenType,
    StewartPartitionStatus,
    TriState,
    VbgExplorerRequest,
)

_COMPLETE_CONTEXT = ExplorerContext(
    known_poor_perfusion_or_hemodynamic_instability=TriState.NO,
    recent_major_ventilation_or_treatment_change=TriState.NO,
    material_preanalytic_concern=TriState.NO,
    supplemental_oxygen=TriState.NO,
)
_BASE_VBG = CurrentVbg(
    ph=7.32,
    pco2=55,
    pco2_unit=Pco2Unit.MMHG,
    base_excess_mmol_l=-2,
    venous_o2_saturation=SaturationInput(75, SaturationUnit.PERCENTAGE_POINTS),
    specimen_type=SpecimenType.PERIPHERAL_VENOUS,
    draw_site=DrawSite.UPPER_EXTREMITY_PERIPHERAL,
)
_BASE_CHEMISTRY = CurrentChemistry(
    sodium_mmol_l=140,
    chloride_mmol_l=105,
    serum_total_co2_mmol_l=24,
    albumin_g_l=40,
    relationship_to_vbg=ChemistryTimeRelationship.SAME_CLINICAL_TIMEPOINT,
)


def _request(
    *,
    vbg: CurrentVbg = _BASE_VBG,
    chemistry: CurrentChemistry = _BASE_CHEMISTRY,
    context: ExplorerContext = _COMPLETE_CONTEXT,
    prior: PriorObservation | None = None,
) -> VbgExplorerRequest:
    return VbgExplorerRequest(
        current_vbg=vbg,
        current_chemistry=chemistry,
        context=context,
        prior_observation=prior,
    )


@pytest.mark.parametrize(
    ("case_id", "case_request", "assertion"),
    [
        (
            "A_complete_current_data",
            _request(),
            lambda result: (
                result.candidate_arterial_region.status is CandidateRegionStatus.AVAILABLE
                and result.state_space.possible_signatures
                and result.state_space.coordinate_view is not None
            ),
        ),
        (
            "B_missing_saturation",
            _request(vbg=replace(_BASE_VBG, venous_o2_saturation=None)),
            lambda result: (
                result.candidate_arterial_region.status is CandidateRegionStatus.UNAVAILABLE
                and result.chemistry.anion_gap_mmol_l == 11
            ),
        ),
        (
            "C_missing_albumin",
            _request(chemistry=replace(_BASE_CHEMISTRY, albumin_g_l=None)),
            lambda result: (
                result.chemistry.corrected_anion_gap_mmol_l is None
                and result.chemistry.stewart_partition.status
                is StewartPartitionStatus.NOT_EVALUABLE
            ),
        ),
        (
            "D_missing_base_excess",
            _request(vbg=replace(_BASE_VBG, base_excess_mmol_l=None)),
            lambda result: (
                result.chemistry.stewart_partition.status is StewartPartitionStatus.NOT_EVALUABLE
                and LimitationCode.RESIDUAL_UNMEASURED_IONS_NOT_IDENTIFIABLE
                in result.chemistry.nonidentifiable_components
            ),
        ),
        (
            "E_central_source",
            _request(
                vbg=replace(
                    _BASE_VBG,
                    specimen_type=SpecimenType.CENTRAL_VENOUS,
                    draw_site=DrawSite.CENTRAL_CATHETER,
                )
            ),
            lambda result: (
                result.candidate_arterial_region.status is CandidateRegionStatus.UNAVAILABLE
                and result.observed_vbg.specimen_type is SpecimenType.CENTRAL_VENOUS
            ),
        ),
        (
            "F_recent_ventilation_change",
            _request(
                context=replace(
                    _COMPLETE_CONTEXT,
                    recent_major_ventilation_or_treatment_change=TriState.YES,
                )
            ),
            lambda result: (
                result.candidate_arterial_region.status is CandidateRegionStatus.UNAVAILABLE
                and result.chemistry.anion_gap_mmol_l == 11
            ),
        ),
        (
            "G_prior_abg",
            _request(
                prior=PriorObservation(
                    observation_type=PriorObservationType.ABG,
                    ph=7.35,
                    pco2=50,
                    pco2_unit=Pco2Unit.MMHG,
                )
            ),
            lambda result: result.longitudinal_context.historical_arterial_coordinate is not None,
        ),
        (
            "H_prior_vbg",
            _request(
                prior=PriorObservation(
                    observation_type=PriorObservationType.VBG,
                    ph=7.28,
                    pco2=60,
                    pco2_unit=Pco2Unit.MMHG,
                    specimen_type=SpecimenType.CENTRAL_VENOUS,
                    draw_site=DrawSite.CENTRAL_CATHETER,
                )
            ),
            lambda result: (
                result.longitudinal_context.historical_arterial_coordinate is None
                and LimitationCode.PRIOR_VBG_REMAINS_VENOUS
                in result.longitudinal_context.limitation_codes
            ),
        ),
        (
            "I_prior_serum_total_co2",
            _request(
                prior=PriorObservation(
                    observation_type=PriorObservationType.SERUM_TOTAL_CO2,
                    serum_total_co2_mmol_l=30,
                )
            ),
            lambda result: (
                result.longitudinal_context.historical_arterial_coordinate is None
                and LimitationCode.PRIOR_SERUM_TOTAL_CO2_REMAINS_CHEMISTRY
                in result.longitudinal_context.limitation_codes
            ),
        ),
    ],
)
def test_synthetic_scientific_matrix(
    case_id: str, case_request: VbgExplorerRequest, assertion: object
) -> None:
    """Each matrix row has only fictional values and one explicit expected composition."""

    result = interpret_vbg(case_request)

    assert callable(assertion)
    assert assertion(result), case_id
