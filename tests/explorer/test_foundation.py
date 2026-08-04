from __future__ import annotations

import json

import pytest

from vbg_interpreter.browser_adapter import interpret_browser_request_json_with
from vbg_interpreter.candidate_region import calculate_candidate_arterial_region
from vbg_interpreter.chemistry import calculate_chemistry_interpretation
from vbg_interpreter.interpret import interpret_vbg
from vbg_interpreter.longitudinal import build_longitudinal_context
from vbg_interpreter.mapping import request_from_json
from vbg_interpreter.models import (
    CandidateRegionReasonCode,
    CandidateRegionStatus,
    CandidateRegionWarningCode,
    ChemistryTimeRelationship,
    CurrentChemistry,
    CurrentVbg,
    DrawSite,
    EvidenceTier,
    ExplorerContext,
    ExplorerInputError,
    GasValueOrigin,
    Hco3Basis,
    LimitationCode,
    Pco2Unit,
    PriorObservation,
    PriorObservationType,
    SaturationInput,
    SaturationUnit,
    SpecimenType,
    TriState,
    VbgExplorerRequest,
)
from vbg_interpreter.normalize import normalize_pco2_to_mmhg, normalize_request
from vbg_interpreter.serialization import ExplorerSerializationError
from vbg_interpreter.venous_gas import complete_venous_gas

_DEFAULT_SATURATION = SaturationInput(
    value=75.0,
    unit=SaturationUnit.PERCENTAGE_POINTS,
)


def _context(**overrides: TriState) -> ExplorerContext:
    values: dict[str, TriState] = {
        "known_poor_perfusion_or_hemodynamic_instability": TriState.NO,
        "recent_major_ventilation_or_treatment_change": TriState.NO,
        "material_preanalytic_concern": TriState.NO,
        "supplemental_oxygen": TriState.NO,
    }
    values.update(overrides)
    return ExplorerContext(**values)


def _request(
    *,
    saturation: SaturationInput | None = _DEFAULT_SATURATION,
    specimen_type: SpecimenType = SpecimenType.PERIPHERAL_VENOUS,
    draw_site: DrawSite = DrawSite.UPPER_EXTREMITY_PERIPHERAL,
    context: ExplorerContext | None = None,
    albumin_g_l: float | None = 40.0,
) -> VbgExplorerRequest:
    return VbgExplorerRequest(
        current_vbg=CurrentVbg(
            ph=7.32,
            pco2=55.0,
            pco2_unit=Pco2Unit.MMHG,
            venous_o2_saturation=saturation,
            specimen_type=specimen_type,
            draw_site=draw_site,
        ),
        current_chemistry=CurrentChemistry(
            sodium_mmol_l=140.0,
            chloride_mmol_l=105.0,
            serum_total_co2_mmol_l=24.0,
            albumin_g_l=albumin_g_l,
            relationship_to_vbg=ChemistryTimeRelationship.SAME_CLINICAL_TIMEPOINT,
        ),
        context=_context() if context is None else context,
    )


def test_explicit_saturation_units_normalize_to_the_same_candidate_region() -> None:
    percentage = _request(
        saturation=SaturationInput(75.0, SaturationUnit.PERCENTAGE_POINTS),
    )
    fraction = _request(
        saturation=SaturationInput(0.75, SaturationUnit.FRACTION_0_TO_1),
    )

    percentage_region = calculate_candidate_arterial_region(percentage)
    fraction_region = calculate_candidate_arterial_region(fraction)

    assert percentage.current_vbg.venous_o2_saturation is not None
    assert percentage.current_vbg.venous_o2_saturation.value == 75.0
    assert fraction.current_vbg.venous_o2_saturation is not None
    assert fraction.current_vbg.venous_o2_saturation.value == 0.75
    assert fraction.current_vbg.venous_o2_saturation.normalized_percentage_points == 75.0
    assert fraction_region.to_dict() == percentage_region.to_dict()


def test_one_percentage_point_is_not_misread_as_one_fraction() -> None:
    one_percent = SaturationInput(1.0, SaturationUnit.PERCENTAGE_POINTS)
    one_fraction = SaturationInput(1.0, SaturationUnit.FRACTION_0_TO_1)

    assert one_percent.normalized_percentage_points == 1.0
    assert one_fraction.normalized_percentage_points == 100.0


def test_complete_candidate_region_uses_generic_ph_and_farkas_paco2_when_eligible() -> None:
    region = calculate_candidate_arterial_region(_request())

    assert region.status is CandidateRegionStatus.AVAILABLE
    assert region.point is not None
    assert region.ph_interval is not None
    assert region.paco2_interval is not None
    assert region.point.ph == pytest.approx(7.353)
    assert region.point.paco2_mmhg == pytest.approx(51.04)
    assert region.ph_interval.lower == pytest.approx(7.22)
    assert region.ph_interval.upper == pytest.approx(7.50)
    assert region.paco2_interval.lower == pytest.approx(45.72)
    assert region.paco2_interval.upper == pytest.approx(56.87)
    assert region.ph_model_id == "generic_peripheral_vbg_offset_v1"
    assert region.paco2_model_id == "farkas_simplified_93_v1"
    assert region.paco2_profile_id == "jorg_2023_no_supplemental_oxygen"
    assert (
        LimitationCode.GENERIC_POPULATION_OFFSET_NOT_INDIVIDUAL_CORRECTION
        in region.limitation_codes
    )


def test_minimal_generic_model_preserves_bloom_orientation_and_source_extrema() -> None:
    region = calculate_candidate_arterial_region(
        VbgExplorerRequest(
            current_vbg=CurrentVbg(
                ph=7.32,
                pco2=55.0,
                pco2_unit=Pco2Unit.MMHG,
            )
        )
    )

    assert region.status is CandidateRegionStatus.AVAILABLE
    assert region.point is not None
    assert region.ph_interval is not None
    assert region.paco2_interval is not None
    assert region.point.ph == pytest.approx(7.353)
    assert region.point.paco2_mmhg == pytest.approx(50.59)
    assert region.ph_interval.lower == pytest.approx(7.22)
    assert region.ph_interval.upper == pytest.approx(7.50)
    assert region.paco2_interval.lower == pytest.approx(29.0)
    assert region.paco2_interval.upper == pytest.approx(75.4)
    assert region.ph_model_id == "generic_peripheral_vbg_offset_v1"
    assert region.paco2_model_id == "generic_peripheral_vbg_offset_v1"
    assert region.ph_evidence is not None
    assert region.paco2_evidence is not None
    assert region.ph_evidence.evidence_tier is EvidenceTier.DERIVATION_ONLY
    assert region.paco2_evidence.evidence_tier is EvidenceTier.DERIVATION_ONLY
    assert set(region.warning_codes) == {
        CandidateRegionWarningCode.GENERIC_MODEL_WITH_UNKNOWN_SPECIMEN,
        CandidateRegionWarningCode.GENERIC_MODEL_WITH_UNKNOWN_DRAW_SITE,
        CandidateRegionWarningCode.GENERIC_MODEL_WITH_UNKNOWN_PERFUSION_CONTEXT,
        CandidateRegionWarningCode.GENERIC_MODEL_WITH_UNKNOWN_VENTILATION_CONTEXT,
        CandidateRegionWarningCode.GENERIC_MODEL_WITH_UNKNOWN_PREANALYTIC_CONTEXT,
    }
    assert LimitationCode.GENERIC_SOURCE_APPLICABILITY_UNKNOWN in region.limitation_codes


def test_unknown_oxygen_uses_the_existing_conservative_profile_without_blocking() -> None:
    region = calculate_candidate_arterial_region(
        _request(context=_context(supplemental_oxygen=TriState.UNKNOWN))
    )

    assert region.status is CandidateRegionStatus.AVAILABLE
    assert region.paco2_profile_id == "jorg_2023_oxygen_unknown_conservative"
    assert region.paco2_interval is not None
    assert region.paco2_interval.lower == pytest.approx(41.84)
    assert region.paco2_interval.upper == pytest.approx(59.78)


@pytest.mark.parametrize(
    ("case", "expected_reason"),
    [
        (
            _request(specimen_type=SpecimenType.CENTRAL_VENOUS),
            CandidateRegionReasonCode.SPECIMEN_OUTSIDE_PERIPHERAL_VENOUS_SCOPE,
        ),
        (
            _request(
                context=_context(
                    recent_major_ventilation_or_treatment_change=TriState.YES,
                )
            ),
            CandidateRegionReasonCode.RECENT_VENTILATION_OR_TREATMENT_CHANGE,
        ),
        (
            _request(
                context=_context(
                    material_preanalytic_concern=TriState.YES,
                )
            ),
            CandidateRegionReasonCode.MATERIAL_PREANALYTIC_CONCERN,
        ),
    ],
)
def test_known_candidate_blockers_are_typed_and_do_not_reject_the_rest_of_the_request(
    case: VbgExplorerRequest,
    expected_reason: CandidateRegionReasonCode,
) -> None:
    region = calculate_candidate_arterial_region(case)
    chemistry = calculate_chemistry_interpretation(case.current_chemistry)

    assert region.status is CandidateRegionStatus.UNAVAILABLE
    assert expected_reason in region.reason_codes
    assert region.point is None
    assert chemistry.anion_gap_mmol_l == pytest.approx(11.0)


@pytest.mark.parametrize(
    "case",
    [
        _request(saturation=None),
        _request(draw_site=DrawSite.UNKNOWN),
        _request(
            context=_context(
                known_poor_perfusion_or_hemodynamic_instability=TriState.UNKNOWN,
            )
        ),
        _request(
            context=_context(
                material_preanalytic_concern=TriState.UNKNOWN,
            )
        ),
    ],
)
def test_missing_or_unknown_model_context_uses_a_warned_generic_scenario_model(
    case: VbgExplorerRequest,
) -> None:
    region = calculate_candidate_arterial_region(case)

    assert region.status is CandidateRegionStatus.AVAILABLE
    assert LimitationCode.GENERIC_SOURCE_APPLICABILITY_UNKNOWN in region.limitation_codes or (
        case.current_vbg.venous_o2_saturation is None
    )


def test_nonpositive_generic_pco2_envelope_refuses_without_clamping() -> None:
    request = VbgExplorerRequest(
        current_vbg=CurrentVbg(
            ph=7.4,
            pco2=26.0,
            pco2_unit=Pco2Unit.MMHG,
        ),
    )

    region = calculate_candidate_arterial_region(request)

    assert region.status is CandidateRegionStatus.MODEL_DOMAIN_REFUSAL
    assert region.reason_codes == (CandidateRegionReasonCode.NONPOSITIVE_PACO2_INTERVAL_ENDPOINT,)
    assert region.point is None


def test_pco2_kpa_conversion_overflow_is_rejected_before_result_serialization() -> None:
    with pytest.raises(ExplorerInputError, match="normalized PCO2"):
        normalize_pco2_to_mmhg(1e308, Pco2Unit.KPA)


@pytest.mark.parametrize(
    ("vbg", "missing_origin"),
    [
        (
            CurrentVbg(ph=7.32, pco2=55.0, pco2_unit=Pco2Unit.MMHG),
            GasValueOrigin.DERIVED_HENDERSON_HASSELBALCH,
        ),
        (
            CurrentVbg(
                ph=7.32,
                hco3_mmol_l=27.0,
                hco3_basis=Hco3Basis.REPORTED,
            ),
            GasValueOrigin.DERIVED_HENDERSON_HASSELBALCH,
        ),
        (
            CurrentVbg(
                pco2=55.0,
                pco2_unit=Pco2Unit.MMHG,
                hco3_mmol_l=27.0,
                hco3_basis=Hco3Basis.REPORTED,
            ),
            GasValueOrigin.DERIVED_HENDERSON_HASSELBALCH,
        ),
    ],
)
def test_any_two_gas_values_complete_the_third_with_explicit_provenance(
    vbg: CurrentVbg,
    missing_origin: GasValueOrigin,
) -> None:
    completed = complete_venous_gas(
        normalize_request(VbgExplorerRequest(current_vbg=vbg)).current_vbg
    )

    assert completed.ph > 0
    assert completed.pco2_mmhg > 0
    assert completed.hco3_mmol_l > 0
    assert missing_origin in {
        completed.ph_origin,
        completed.pco2_origin,
        completed.hco3_origin,
    }


@pytest.mark.parametrize(
    "current_vbg",
    [
        CurrentVbg(
            pco2=5e-324,
            pco2_unit=Pco2Unit.MMHG,
            hco3_mmol_l=1e308,
            hco3_basis=Hco3Basis.REPORTED,
        ),
        CurrentVbg(
            pco2=1e308,
            pco2_unit=Pco2Unit.MMHG,
            hco3_mmol_l=1e-300,
            hco3_basis=Hco3Basis.REPORTED,
        ),
    ],
)
def test_extreme_finite_ph_completion_failures_use_typed_input_error(
    current_vbg: CurrentVbg,
) -> None:
    with pytest.raises(ExplorerInputError, match="pH completion.*numerical domain"):
        interpret_vbg(VbgExplorerRequest(current_vbg=current_vbg))


def test_three_gas_values_are_preserved_and_material_discordance_is_flagged() -> None:
    vbg = CurrentVbg(
        ph=7.32,
        pco2=55.0,
        pco2_unit=Pco2Unit.MMHG,
        hco3_mmol_l=40.0,
        hco3_basis=Hco3Basis.REPORTED,
    )
    completed = complete_venous_gas(
        normalize_request(VbgExplorerRequest(current_vbg=vbg)).current_vbg
    )

    assert completed.hco3_mmol_l == 40.0
    assert completed.hco3_ph_pco2_comparator_mmol_l is not None
    assert LimitationCode.HCO3_INPUT_DISCORDANT_WITH_PH_PCO2 in completed.limitation_codes


def test_current_vbg_rejects_fewer_than_two_core_gas_values() -> None:
    with pytest.raises(ExplorerInputError, match="at least two"):
        CurrentVbg(ph=7.32)
    with pytest.raises(ExplorerInputError, match="at least two"):
        CurrentVbg()


def test_chemistry_rejects_inputs_that_cannot_yield_a_finite_anion_gap() -> None:
    with pytest.raises(ExplorerInputError, match="finite anion gap"):
        CurrentChemistry(
            sodium_mmol_l=140.0,
            chloride_mmol_l=1e308,
            serum_total_co2_mmol_l=1e308,
        )


def test_chemistry_uses_serum_total_co2_without_imputation_or_paco2_inversion() -> None:
    chemistry = calculate_chemistry_interpretation(_request(albumin_g_l=None).current_chemistry)

    assert chemistry.serum_total_co2_mmol_l == 24.0
    assert chemistry.anion_gap_mmol_l == pytest.approx(11.0)
    assert chemistry.corrected_anion_gap_mmol_l is None
    assert LimitationCode.ALBUMIN_CORRECTION_NOT_EVALUABLE in chemistry.limitation_codes
    assert LimitationCode.SERUM_TOTAL_CO2_IS_NOT_BLOOD_GAS_HCO3 in chemistry.limitation_codes
    assert LimitationCode.NO_CURRENT_PACO2_FROM_CHEMISTRY_ONLY in chemistry.limitation_codes
    assert not hasattr(chemistry, "pco2_mmhg")


def test_albumin_correction_is_calculated_only_when_albumin_is_supplied() -> None:
    chemistry = calculate_chemistry_interpretation(_request(albumin_g_l=35.0).current_chemistry)

    assert chemistry.corrected_anion_gap_mmol_l == pytest.approx(12.25)
    assert LimitationCode.ALBUMIN_CORRECTION_NOT_EVALUABLE not in chemistry.limitation_codes


def test_prior_vbg_remains_venous_and_is_not_historical_arterial_coordinate() -> None:
    prior = PriorObservation(
        observation_type=PriorObservationType.VBG,
        ph=7.28,
        pco2=8.0,
        pco2_unit=Pco2Unit.KPA,
        specimen_type=SpecimenType.CENTRAL_VENOUS,
        draw_site=DrawSite.CENTRAL_CATHETER,
    )
    normalized = normalize_request(
        VbgExplorerRequest(
            current_vbg=_request().current_vbg,
            current_chemistry=_request().current_chemistry,
            context=_context(),
            prior_observation=prior,
        )
    )

    context = build_longitudinal_context(normalized.prior_observation)

    assert context.prior_observation is not None
    assert context.prior_observation.pco2_mmhg == pytest.approx(60.00493461633358)
    assert context.historical_arterial_coordinate is None
    assert LimitationCode.PRIOR_VBG_REMAINS_VENOUS in context.limitation_codes


def test_strict_mapping_requires_decimal_strings_exact_fields_and_duplicate_free_json() -> None:
    payload = {
        "schema_version": "vbg_explorer_request/2.0",
        "current_vbg": {
            "ph": "7.32",
            "pco2": "55",
            "pco2_unit": "mmHg",
            "hco3_mmol_l": None,
            "hco3_basis": "UNKNOWN",
            "base_excess_mmol_l": None,
            "venous_o2_saturation": {"value": "0.75", "unit": "FRACTION_0_TO_1"},
            "specimen_type": "PERIPHERAL_VENOUS",
            "draw_site": "UPPER_EXTREMITY_PERIPHERAL",
        },
        "current_chemistry": {
            "sodium_mmol_l": "140",
            "chloride_mmol_l": "105",
            "serum_total_co2_mmol_l": "24",
            "albumin_g_l": None,
            "lactate_mmol_l": None,
            "relationship_to_vbg": "UNKNOWN",
        },
        "context": {
            "known_poor_perfusion_or_hemodynamic_instability": "NO",
            "recent_major_ventilation_or_treatment_change": "NO",
            "material_preanalytic_concern": "NO",
            "supplemental_oxygen": "UNKNOWN",
        },
        "prior_observation": None,
    }

    request = request_from_json(json.dumps(payload))
    rendered = interpret_browser_request_json_with(
        json.dumps(payload),
        lambda value: {
            "schema_version": "test",
            "normalized_saturation": value.current_vbg.venous_o2_saturation,
        },
    )

    assert request.current_vbg.venous_o2_saturation is not None
    assert request.current_vbg.venous_o2_saturation.normalized_percentage_points == 75.0
    assert (
        json.loads(rendered)["result"]["normalized_saturation"]["normalized_percentage_points"]
        == 75.0
    )
    minimal_payload = json.loads(json.dumps(payload))
    minimal_payload["current_vbg"].update(
        {
            "ph": None,
            "pco2": "55",
            "pco2_unit": "mmHg",
            "hco3_mmol_l": "27",
            "hco3_basis": "REPORTED",
        }
    )
    minimal_payload["current_chemistry"].update(
        {
            "sodium_mmol_l": None,
            "chloride_mmol_l": None,
            "serum_total_co2_mmol_l": None,
        }
    )
    minimal_request = request_from_json(json.dumps(minimal_payload))
    assert minimal_request.current_vbg.ph is None
    assert minimal_request.current_vbg.pco2 == 55.0
    assert minimal_request.current_chemistry.sodium_mmol_l is None
    with pytest.raises(ExplorerSerializationError):
        request_from_json('{"schema_version":"vbg_explorer_request/2.0","schema_version":"x"}')
    payload["current_vbg"]["ph"] = 7.32
    with pytest.raises(ExplorerSerializationError):
        request_from_json(json.dumps(payload))
