"""End-to-end progressive composition tests using synthetic inputs only."""

from __future__ import annotations

import pytest

from vbg_interpreter.interpret import interpret_vbg
from vbg_interpreter.models import (
    CandidateRegionStatus,
    ChemistryTimeRelationship,
    CurrentChemistry,
    CurrentVbg,
    DrawSite,
    ExplorerContext,
    FeatureConclusionStatus,
    LimitationCode,
    Pco2Unit,
    PriorObservation,
    PriorObservationType,
    SaturationInput,
    SaturationUnit,
    SpecimenType,
    StateEnumerationStatus,
    TriState,
    VbgExplorerRequest,
)

_DEFAULT_SATURATION = SaturationInput(75, SaturationUnit.PERCENTAGE_POINTS)


def _request(
    *,
    saturation: SaturationInput | None = _DEFAULT_SATURATION,
    specimen: SpecimenType = SpecimenType.PERIPHERAL_VENOUS,
    site: DrawSite = DrawSite.UPPER_EXTREMITY_PERIPHERAL,
    context: ExplorerContext | None = None,
    albumin: float | None = 40.0,
    base_excess: float | None = -2.0,
    prior: PriorObservation | None = None,
) -> VbgExplorerRequest:
    return VbgExplorerRequest(
        current_vbg=CurrentVbg(
            ph=7.32,
            pco2=55,
            pco2_unit=Pco2Unit.MMHG,
            base_excess_mmol_l=base_excess,
            venous_o2_saturation=saturation,
            specimen_type=specimen,
            draw_site=site,
        ),
        current_chemistry=CurrentChemistry(
            sodium_mmol_l=140,
            chloride_mmol_l=105,
            serum_total_co2_mmol_l=24,
            albumin_g_l=albumin,
            relationship_to_vbg=ChemistryTimeRelationship.SAME_CLINICAL_TIMEPOINT,
        ),
        context=context
        or ExplorerContext(
            known_poor_perfusion_or_hemodynamic_instability=TriState.NO,
            recent_major_ventilation_or_treatment_change=TriState.NO,
            material_preanalytic_concern=TriState.NO,
            supplemental_oxygen=TriState.NO,
        ),
        prior_observation=prior,
    )


def test_complete_data_returns_set_valued_candidate_state_space_and_chemistry() -> None:
    result = interpret_vbg(_request())

    assert result.provenance.software_version == "0.1.0"
    assert result.candidate_arterial_region.status is CandidateRegionStatus.AVAILABLE
    assert result.state_space.enumeration_status is StateEnumerationStatus.CERTIFIED_EXHAUSTIVE
    assert result.state_space.possible_signatures
    assert result.state_space.coordinate_view is not None
    assert result.chemistry.corrected_anion_gap_mmol_l == pytest.approx(11.0)


def test_missing_saturation_keeps_observed_and_chemistry_but_withholds_arterial_state_claims() -> (
    None
):
    result = interpret_vbg(_request(saturation=None))

    assert result.observed_vbg.ph == pytest.approx(7.32)
    assert result.chemistry.anion_gap_mmol_l == pytest.approx(11.0)
    assert result.candidate_arterial_region.status is CandidateRegionStatus.UNAVAILABLE
    assert result.state_space.enumeration_status is StateEnumerationStatus.NOT_EVALUATED
    assert not result.state_space.possible_signatures
    assert "SAME_SAMPLE_VENOUS_SATURATION" in {
        code.value for code in result.information_that_would_reduce_ambiguity
    }


@pytest.mark.parametrize(
    ("specimen", "site"),
    [
        (SpecimenType.CENTRAL_VENOUS, DrawSite.CENTRAL_CATHETER),
        (SpecimenType.UNKNOWN, DrawSite.UNKNOWN),
    ],
)
def test_nonperipheral_or_unknown_source_withholds_only_arterialization(
    specimen: SpecimenType,
    site: DrawSite,
) -> None:
    result = interpret_vbg(_request(specimen=specimen, site=site))

    assert result.candidate_arterial_region.status is CandidateRegionStatus.UNAVAILABLE
    assert result.chemistry.anion_gap_mmol_l == pytest.approx(11.0)
    assert result.observed_vbg.specimen_type is specimen


def test_recent_ventilation_change_blocks_model_not_observed_or_chemistry_lanes() -> None:
    result = interpret_vbg(
        _request(
            context=ExplorerContext(
                known_poor_perfusion_or_hemodynamic_instability=TriState.NO,
                recent_major_ventilation_or_treatment_change=TriState.YES,
                material_preanalytic_concern=TriState.NO,
                supplemental_oxygen=TriState.NO,
            )
        )
    )

    assert result.candidate_arterial_region.status is CandidateRegionStatus.UNAVAILABLE
    assert result.state_space.enumeration_status is StateEnumerationStatus.NOT_EVALUATED
    assert result.chemistry.anion_gap_mmol_l == pytest.approx(11.0)


def test_uncertified_extreme_state_space_publishes_no_component_or_exclusion_claims() -> None:
    request = _request()
    result = interpret_vbg(
        VbgExplorerRequest(
            current_vbg=CurrentVbg(
                ph=1e100,
                pco2=request.current_vbg.pco2,
                pco2_unit=request.current_vbg.pco2_unit,
                base_excess_mmol_l=request.current_vbg.base_excess_mmol_l,
                venous_o2_saturation=request.current_vbg.venous_o2_saturation,
                specimen_type=request.current_vbg.specimen_type,
                draw_site=request.current_vbg.draw_site,
            ),
            current_chemistry=request.current_chemistry,
            context=request.context,
        )
    )

    assert result.candidate_arterial_region.status is CandidateRegionStatus.AVAILABLE
    assert result.state_space.enumeration_status is StateEnumerationStatus.CERTIFICATION_FAILED
    assert not result.state_space.possible_signatures
    assert {item.status for item in result.state_space.feature_conclusions} == {
        FeatureConclusionStatus.NOT_EVALUABLE
    }
    assert result.chemistry.anion_gap_mmol_l == pytest.approx(11.0)


def test_prior_abg_is_historical_context_without_pruning_chronicity_branches() -> None:
    result = interpret_vbg(
        _request(
            prior=PriorObservation(
                observation_type=PriorObservationType.ABG,
                elapsed_hours=12,
                ph=7.35,
                pco2=50,
                pco2_unit=Pco2Unit.MMHG,
                intervening_major_ventilation_or_treatment_change=TriState.UNKNOWN,
            )
        )
    )

    assert result.longitudinal_context.historical_arterial_coordinate is not None
    assert {
        signature.chronicity_branch.value for signature in result.state_space.possible_signatures
    } == {
        "CHRONIC_FLAGGED",
        "NOT_CHRONIC_FLAGGED",
    }
    assert LimitationCode.INTERVENING_CHANGE_UNKNOWN in result.longitudinal_context.limitation_codes


def test_prior_vbg_and_serum_total_co2_remain_in_their_own_provenance_lanes() -> None:
    prior_vbg = PriorObservation(
        observation_type=PriorObservationType.VBG,
        ph=7.28,
        pco2=60,
        pco2_unit=Pco2Unit.MMHG,
        specimen_type=SpecimenType.CENTRAL_VENOUS,
        draw_site=DrawSite.CENTRAL_CATHETER,
    )
    vbg_result = interpret_vbg(_request(prior=prior_vbg))
    assert vbg_result.longitudinal_context.historical_arterial_coordinate is None
    assert (
        LimitationCode.PRIOR_VBG_REMAINS_VENOUS in vbg_result.longitudinal_context.limitation_codes
    )

    prior_chemistry = PriorObservation(
        observation_type=PriorObservationType.SERUM_TOTAL_CO2,
        serum_total_co2_mmol_l=30,
    )
    chemistry_result = interpret_vbg(_request(prior=prior_chemistry))
    assert chemistry_result.longitudinal_context.historical_arterial_coordinate is None
    assert (
        LimitationCode.PRIOR_SERUM_TOTAL_CO2_REMAINS_CHEMISTRY
        in chemistry_result.longitudinal_context.limitation_codes
    )
