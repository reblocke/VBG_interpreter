"""Frozen, local evidence records for retained explorer calculations.

The reset deliberately has no model registry loader.  These records reproduce the
approved Farkas/Jorg component constants without importing the superseded runtime.
"""

from __future__ import annotations

from dataclasses import dataclass

from vbg_interpreter.models import (
    CalculationMetadata,
    EvidenceDescriptor,
    EvidenceTier,
    ExplorerProvenance,
    TriState,
)
from vbg_interpreter.version import VERSION

FARKAS_SIMPLIFIED_MODEL_ID = "farkas_simplified_93_v1"
FARKAS_SIMPLIFIED_MODEL_VERSION = "1.0.0"
FARKAS_SATURATION_REFERENCE_PERCENT = 93.0
FARKAS_PH_COEFFICIENT_PER_PERCENTAGE_POINT = 0.0011
FARKAS_PACO2_COEFFICIENT_MMHG_PER_PERCENTAGE_POINT = -0.22
FARKAS_PH_UNCERTAINTY_PROFILE_ID = "farkas_2012_ph_approx_error_band"
FARKAS_PH_UNCERTAINTY_LOWER_OFFSET = -0.03
FARKAS_PH_UNCERTAINTY_UPPER_OFFSET = 0.03
FARKAS_PH_UNCERTAINTY_LABEL = "source-reported approximate 95% error band"
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


PH_EVIDENCE = EvidenceDescriptor(
    evidence_tier=EvidenceTier.DERIVATION_ONLY,
    external_validation=False,
    source_ids=("farkas_2012_public_manuscript",),
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


def explorer_provenance() -> ExplorerProvenance:
    """Return the fixed provenance record included in every full explorer result."""

    return ExplorerProvenance(
        software_version=VERSION,
        candidate_region_model_id=FARKAS_SIMPLIFIED_MODEL_ID,
        candidate_region_model_version=FARKAS_SIMPLIFIED_MODEL_VERSION,
        ph_evidence=PH_EVIDENCE,
        paco2_evidence=PACO2_EVIDENCE,
        boston_ruleset_id=BOSTON_RULESET_ID,
    )
