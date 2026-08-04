"""Frozen, local evidence records for the Explorer's retained components.

The package deliberately has no model-registry loader.  These records keep the
reviewed Bloom generic sensitivity parameters and the Farkas/Jörg PaCO2 upgrade
local and explicit.
"""

from __future__ import annotations

from dataclasses import dataclass

from vbg_interpreter.models import (
    CalculationMetadata,
    CandidateArterialRegion,
    CandidateRegionStatus,
    EvidenceDescriptor,
    EvidenceTier,
    ExplorerProvenance,
    TriState,
)
from vbg_interpreter.version import VERSION

FARKAS_SIMPLIFIED_MODEL_ID = "farkas_simplified_93_v1"
FARKAS_SIMPLIFIED_MODEL_VERSION = "1.0.0"
COMPONENT_SELECTED_CANDIDATE_MODEL_ID = "component_selected_candidate_region_v2"
COMPONENT_SELECTED_CANDIDATE_MODEL_VERSION = "2.0.0"
GENERIC_PERIPHERAL_OFFSET_MODEL_ID = "generic_peripheral_vbg_offset_v1"
GENERIC_PERIPHERAL_OFFSET_MODEL_VERSION = "1.0.0"
GENERIC_PH_POINT_OFFSET = 0.033
GENERIC_PH_LOWER_OFFSET = -0.10
GENERIC_PH_UPPER_OFFSET = 0.18
GENERIC_PH_PROFILE_ID = "bloom_2014_published_study_extrema_ph"
GENERIC_PACO2_POINT_OFFSET_MMHG = -4.41
GENERIC_PACO2_LOWER_OFFSET_MMHG = -26.0
GENERIC_PACO2_UPPER_OFFSET_MMHG = 20.4
GENERIC_PACO2_PROFILE_ID = "bloom_2014_published_study_extrema_pco2"
GENERIC_SCENARIO_ENVELOPE_LABEL = "published study-level agreement-extrema scenario envelope"
FARKAS_SATURATION_REFERENCE_PERCENT = 93.0
FARKAS_PACO2_COEFFICIENT_MMHG_PER_PERCENTAGE_POINT = -0.22
PACO2_INTERVAL_LABEL = "arterial-reference sensitivity range"
PACO2_ERROR_CONVENTION = "estimate_minus_arterial_reference"
BOSTON_RULESET_ID = "stewartlight_boston_ruleset_v1"
MMHG_PER_KPA = 7.500616827041697


@dataclass(frozen=True, slots=True)
class Paco2UncertaintyProfile:
    profile_id: str
    context: str
    error_loa_lower_mmhg: float
    error_loa_upper_mmhg: float
    source_ids: tuple[str, ...]


GENERIC_PH_EVIDENCE = EvidenceDescriptor(
    evidence_tier=EvidenceTier.DERIVATION_ONLY,
    external_validation=False,
    source_ids=("bloom_2014",),
)
GENERIC_PACO2_EVIDENCE = EvidenceDescriptor(
    evidence_tier=EvidenceTier.DERIVATION_ONLY,
    external_validation=False,
    source_ids=("bloom_2014",),
)
DERIVED_AXIS_GENERIC_EVIDENCE = EvidenceDescriptor(
    evidence_tier=EvidenceTier.DERIVATION_ONLY,
    external_validation=False,
    source_ids=("bloom_2014", "henderson_hasselbalch_documented_constants_v1"),
)
DERIVED_FARKAS_PACO2_EVIDENCE = EvidenceDescriptor(
    evidence_tier=EvidenceTier.DERIVATION_ONLY,
    external_validation=False,
    source_ids=(
        "farkas_2012_public_manuscript",
        "jorg_2023",
        "henderson_hasselbalch_documented_constants_v1",
    ),
)
PACO2_EVIDENCE = EvidenceDescriptor(
    evidence_tier=EvidenceTier.EXTERNALLY_EVALUATED,
    external_validation=True,
    source_ids=("farkas_2012_public_manuscript", "jorg_2023"),
)
SERUM_ANION_GAP_METADATA = CalculationMetadata(
    method_id="serum_anion_gap_na_minus_cl_minus_total_co2_v1",
    evidence=EvidenceDescriptor(
        evidence_tier=EvidenceTier.DERIVED_CALCULATION,
        external_validation=False,
        source_ids=("explorer_documented_serum_anion_gap_formula_v1",),
    ),
)
ALBUMIN_CORRECTED_ANION_GAP_METADATA = CalculationMetadata(
    method_id="albumin_corrected_serum_anion_gap_v1",
    evidence=EvidenceDescriptor(
        evidence_tier=EvidenceTier.DERIVED_CALCULATION,
        external_validation=False,
        source_ids=("explorer_documented_albumin_ag_formula_v1",),
    ),
)
VENOUS_STEWART_PARTITION_METADATA = CalculationMetadata(
    method_id="stewartlight_specimen_neutral_partition_venous_basis_v1",
    evidence=EvidenceDescriptor(
        evidence_tier=EvidenceTier.IMPLEMENTED_SOFTWARE_RULESET,
        external_validation=False,
        source_ids=("stewartlight_structured_partition@f277cac",),
    ),
)

PACO2_PROFILES = {
    TriState.NO: Paco2UncertaintyProfile(
        profile_id="jorg_2023_no_supplemental_oxygen",
        context="supplemental_oxygen_no",
        error_loa_lower_mmhg=-5.83,
        error_loa_upper_mmhg=5.32,
        source_ids=("jorg_2023",),
    ),
    TriState.YES: Paco2UncertaintyProfile(
        profile_id="jorg_2023_supplemental_oxygen",
        context="supplemental_oxygen_yes",
        error_loa_lower_mmhg=-8.74,
        error_loa_upper_mmhg=9.2,
        source_ids=("jorg_2023",),
    ),
    TriState.UNKNOWN: Paco2UncertaintyProfile(
        profile_id="jorg_2023_oxygen_unknown_conservative",
        context="supplemental_oxygen_unknown",
        error_loa_lower_mmhg=-8.74,
        error_loa_upper_mmhg=9.2,
        source_ids=("jorg_2023",),
    ),
}


def paco2_profile_for_oxygen(status: TriState) -> Paco2UncertaintyProfile:
    """Select the approved oxygen-stratified sensitivity profile."""

    if not isinstance(status, TriState):
        raise TypeError("supplemental_oxygen must be TriState.")
    return PACO2_PROFILES[status]


def explorer_provenance(
    candidate_region: CandidateArterialRegion | None = None,
) -> ExplorerProvenance:
    """Return provenance using the selected or attempted component evidence."""

    if candidate_region is not None and not isinstance(candidate_region, CandidateArterialRegion):
        raise TypeError("candidate_region must be CandidateArterialRegion or None.")
    ph_evidence = GENERIC_PH_EVIDENCE
    paco2_evidence = GENERIC_PACO2_EVIDENCE
    if candidate_region is not None and candidate_region.status in {
        CandidateRegionStatus.AVAILABLE,
        CandidateRegionStatus.MODEL_DOMAIN_REFUSAL,
    }:
        if candidate_region.ph_evidence is None or candidate_region.paco2_evidence is None:
            raise AssertionError("Attempted candidate models require component evidence.")
        ph_evidence = candidate_region.ph_evidence
        paco2_evidence = candidate_region.paco2_evidence

    return ExplorerProvenance(
        software_version=VERSION,
        candidate_region_model_id=COMPONENT_SELECTED_CANDIDATE_MODEL_ID,
        candidate_region_model_version=COMPONENT_SELECTED_CANDIDATE_MODEL_VERSION,
        ph_evidence=ph_evidence,
        paco2_evidence=paco2_evidence,
        boston_ruleset_id=BOSTON_RULESET_ID,
    )
