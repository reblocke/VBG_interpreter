"""Typed contracts for the single VBG Acid--Base Explorer product."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum

from vbg_interpreter.serialization import to_primitive
from vbg_interpreter.version import VERSION

VBG_EXPLORER_REQUEST_SCHEMA_VERSION = "vbg_explorer_request/2.0"
VBG_EXPLORER_RESULT_SCHEMA_VERSION = "vbg_explorer_result/2.0"


class ExplorerInputError(ValueError):
    """Raised when a typed explorer input is physically or structurally invalid."""


class TriState(StrEnum):
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


class Pco2Unit(StrEnum):
    MMHG = "mmHg"
    KPA = "kPa"


class SaturationUnit(StrEnum):
    PERCENTAGE_POINTS = "PERCENTAGE_POINTS"
    FRACTION_0_TO_1 = "FRACTION_0_TO_1"


class Hco3Basis(StrEnum):
    REPORTED = "REPORTED"
    CALCULATED = "CALCULATED"
    UNKNOWN = "UNKNOWN"


class GasValueOrigin(StrEnum):
    """Whether a completed venous-gas coordinate was supplied or calculated."""

    SUPPLIED = "SUPPLIED"
    DERIVED_HENDERSON_HASSELBALCH = "DERIVED_HENDERSON_HASSELBALCH"


class VenousOrientationCode(StrEnum):
    """Descriptive pH orientation; never a Boston process classification."""

    BELOW_RULESET_REFERENCE_BAND = "BELOW_RULESET_REFERENCE_BAND"
    WITHIN_RULESET_REFERENCE_BAND = "WITHIN_RULESET_REFERENCE_BAND"
    ABOVE_RULESET_REFERENCE_BAND = "ABOVE_RULESET_REFERENCE_BAND"


class SpecimenType(StrEnum):
    PERIPHERAL_VENOUS = "PERIPHERAL_VENOUS"
    CENTRAL_VENOUS = "CENTRAL_VENOUS"
    MIXED_VENOUS = "MIXED_VENOUS"
    CAPILLARY = "CAPILLARY"
    UNKNOWN = "UNKNOWN"


class DrawSite(StrEnum):
    UPPER_EXTREMITY_PERIPHERAL = "UPPER_EXTREMITY_PERIPHERAL"
    LOWER_EXTREMITY_PERIPHERAL = "LOWER_EXTREMITY_PERIPHERAL"
    FEMORAL = "FEMORAL"
    CENTRAL_CATHETER = "CENTRAL_CATHETER"
    PULMONARY_ARTERY_CATHETER = "PULMONARY_ARTERY_CATHETER"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class ChemistryTimeRelationship(StrEnum):
    SAME_CLINICAL_TIMEPOINT = "SAME_CLINICAL_TIMEPOINT"
    DIFFERENT_TIMEPOINT = "DIFFERENT_TIMEPOINT"
    UNKNOWN = "UNKNOWN"


class PriorObservationType(StrEnum):
    ABG = "ABG"
    VBG = "VBG"
    SERUM_TOTAL_CO2 = "SERUM_TOTAL_CO2"


class EvidenceTier(StrEnum):
    MEASURED_REPORTED_VENOUS = "measured_reported_venous"
    DERIVATION_ONLY = "derivation_only"
    EXTERNALLY_EVALUATED = "externally_evaluated"
    DERIVED_CALCULATION = "derived_calculation"
    IMPLEMENTED_SOFTWARE_RULESET = "implemented_software_ruleset"


class CandidateRegionStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    MODEL_DOMAIN_REFUSAL = "MODEL_DOMAIN_REFUSAL"


class CandidateRegionReasonCode(StrEnum):
    SPECIMEN_OUTSIDE_PERIPHERAL_VENOUS_SCOPE = "SPECIMEN_OUTSIDE_PERIPHERAL_VENOUS_SCOPE"
    DRAW_SITE_OUTSIDE_UPPER_EXTREMITY_SCOPE = "DRAW_SITE_OUTSIDE_UPPER_EXTREMITY_SCOPE"
    KNOWN_POOR_PERFUSION_OR_HEMODYNAMIC_INSTABILITY = (
        "KNOWN_POOR_PERFUSION_OR_HEMODYNAMIC_INSTABILITY"
    )
    RECENT_VENTILATION_OR_TREATMENT_CHANGE = "RECENT_VENTILATION_OR_TREATMENT_CHANGE"
    MATERIAL_PREANALYTIC_CONCERN = "MATERIAL_PREANALYTIC_CONCERN"
    NONFINITE_MODEL_OUTPUT = "NONFINITE_MODEL_OUTPUT"
    NONPOSITIVE_ESTIMATED_PH = "NONPOSITIVE_ESTIMATED_PH"
    NONPOSITIVE_ESTIMATED_PACO2 = "NONPOSITIVE_ESTIMATED_PACO2"
    NONPOSITIVE_PH_INTERVAL_ENDPOINT = "NONPOSITIVE_PH_INTERVAL_ENDPOINT"
    NONPOSITIVE_PACO2_INTERVAL_ENDPOINT = "NONPOSITIVE_PACO2_INTERVAL_ENDPOINT"
    INVALID_INTERVAL_ORDER = "INVALID_INTERVAL_ORDER"


class CandidateRegionWarningCode(StrEnum):
    SATURATION_ABOVE_SIMPLIFIED_REFERENCE = "SATURATION_ABOVE_SIMPLIFIED_REFERENCE"
    GENERIC_MODEL_WITH_UNKNOWN_SPECIMEN = "GENERIC_MODEL_WITH_UNKNOWN_SPECIMEN"
    GENERIC_MODEL_WITH_UNKNOWN_DRAW_SITE = "GENERIC_MODEL_WITH_UNKNOWN_DRAW_SITE"
    GENERIC_MODEL_WITH_UNKNOWN_PERFUSION_CONTEXT = "GENERIC_MODEL_WITH_UNKNOWN_PERFUSION_CONTEXT"
    GENERIC_MODEL_WITH_UNKNOWN_VENTILATION_CONTEXT = (
        "GENERIC_MODEL_WITH_UNKNOWN_VENTILATION_CONTEXT"
    )
    GENERIC_MODEL_WITH_UNKNOWN_PREANALYTIC_CONTEXT = (
        "GENERIC_MODEL_WITH_UNKNOWN_PREANALYTIC_CONTEXT"
    )


class LimitationCode(StrEnum):
    NO_ARTERIAL_OXYGENATION_INFERENCE_FROM_VBG = "NO_ARTERIAL_OXYGENATION_INFERENCE_FROM_VBG"
    SOURCE_SPECTRUM_NOT_ESTABLISHED = "SOURCE_SPECTRUM_NOT_ESTABLISHED"
    SERUM_TOTAL_CO2_IS_NOT_BLOOD_GAS_HCO3 = "SERUM_TOTAL_CO2_IS_NOT_BLOOD_GAS_HCO3"
    NO_CURRENT_PACO2_FROM_CHEMISTRY_ONLY = "NO_CURRENT_PACO2_FROM_CHEMISTRY_ONLY"
    ALBUMIN_CORRECTION_NOT_EVALUABLE = "ALBUMIN_CORRECTION_NOT_EVALUABLE"
    STEWART_PARTITION_NOT_EVALUABLE = "STEWART_PARTITION_NOT_EVALUABLE"
    STEWART_PARTITION_NUMERICAL_DOMAIN_REFUSAL = "STEWART_PARTITION_NUMERICAL_DOMAIN_REFUSAL"
    BASE_EXCESS_REQUIRED_FOR_STEWART_PARTITION = "BASE_EXCESS_REQUIRED_FOR_STEWART_PARTITION"
    ALBUMIN_REQUIRED_FOR_STEWART_PARTITION = "ALBUMIN_REQUIRED_FOR_STEWART_PARTITION"
    CHEMISTRY_TIME_RELATIONSHIP_NOT_SAME = "CHEMISTRY_TIME_RELATIONSHIP_NOT_SAME"
    RESIDUAL_UNMEASURED_IONS_NOT_IDENTIFIABLE = "RESIDUAL_UNMEASURED_IONS_NOT_IDENTIFIABLE"
    PRIOR_OBSERVATION_NOT_PROVIDED = "PRIOR_OBSERVATION_NOT_PROVIDED"
    PRIOR_VBG_REMAINS_VENOUS = "PRIOR_VBG_REMAINS_VENOUS"
    PRIOR_SERUM_TOTAL_CO2_REMAINS_CHEMISTRY = "PRIOR_SERUM_TOTAL_CO2_REMAINS_CHEMISTRY"
    INTERVENING_CHANGE_UNKNOWN = "INTERVENING_CHANGE_UNKNOWN"
    INTERVENING_CHANGE_REPORTED = "INTERVENING_CHANGE_REPORTED"
    BOSTON_STATE_SPACE_CERTIFICATION_FAILED = "BOSTON_STATE_SPACE_CERTIFICATION_FAILED"
    GENERIC_POPULATION_OFFSET_NOT_INDIVIDUAL_CORRECTION = (
        "GENERIC_POPULATION_OFFSET_NOT_INDIVIDUAL_CORRECTION"
    )
    VENOUS_ONLY_ORIENTATION = "VENOUS_ONLY_ORIENTATION"
    HCO3_INPUT_DISCORDANT_WITH_PH_PCO2 = "HCO3_INPUT_DISCORDANT_WITH_PH_PCO2"
    ANION_GAP_NOT_EVALUABLE_MISSING_OPERANDS = "ANION_GAP_NOT_EVALUABLE_MISSING_OPERANDS"
    DERIVED_VENOUS_AXIS_OUTSIDE_POPULATION_MODEL_EVALUATION = (
        "DERIVED_VENOUS_AXIS_OUTSIDE_POPULATION_MODEL_EVALUATION"
    )
    GENERIC_STUDY_RANGE_NOT_CALIBRATED_PREDICTION_INTERVAL = (
        "GENERIC_STUDY_RANGE_NOT_CALIBRATED_PREDICTION_INTERVAL"
    )
    GENERIC_AXES_NOT_JOINTLY_VALIDATED = "GENERIC_AXES_NOT_JOINTLY_VALIDATED"
    GENERIC_SOURCE_APPLICABILITY_UNKNOWN = "GENERIC_SOURCE_APPLICABILITY_UNKNOWN"


class InformationNeedCode(StrEnum):
    ARTERIAL_BLOOD_GAS_IF_ARTERIAL_CONFIRMATION_REQUIRED = (
        "ARTERIAL_BLOOD_GAS_IF_ARTERIAL_CONFIRMATION_REQUIRED"
    )
    SAME_SAMPLE_VENOUS_SATURATION = "SAME_SAMPLE_VENOUS_SATURATION"
    MEASURED_VENOUS_PH = "MEASURED_VENOUS_PH"
    MEASURED_VENOUS_PCO2 = "MEASURED_VENOUS_PCO2"
    PERIPHERAL_UPPER_EXTREMITY_SPECIMEN_AND_SITE = "PERIPHERAL_UPPER_EXTREMITY_SPECIMEN_AND_SITE"
    PERFUSION_AND_HEMODYNAMIC_CONTEXT = "PERFUSION_AND_HEMODYNAMIC_CONTEXT"
    VENTILATION_OR_TREATMENT_CHANGE_CONTEXT = "VENTILATION_OR_TREATMENT_CHANGE_CONTEXT"
    PREANALYTIC_CONTEXT = "PREANALYTIC_CONTEXT"
    ALBUMIN = "ALBUMIN"
    BASE_EXCESS = "BASE_EXCESS"
    COMPARABLE_PRIOR_GAS_OR_CHEMISTRY = "COMPARABLE_PRIOR_GAS_OR_CHEMISTRY"
    SODIUM = "SODIUM"
    CHLORIDE = "CHLORIDE"
    SERUM_TOTAL_CO2 = "SERUM_TOTAL_CO2"


class ChemistryStatus(StrEnum):
    NOT_PROVIDED = "NOT_PROVIDED"
    PARTIAL = "PARTIAL"
    COMPLETED = "COMPLETED"


class StewartPartitionStatus(StrEnum):
    COMPLETED = "COMPLETED"
    NOT_EVALUABLE = "NOT_EVALUABLE"
    MODEL_DOMAIN_REFUSAL = "MODEL_DOMAIN_REFUSAL"


class LongitudinalStatus(StrEnum):
    NOT_PROVIDED = "NOT_PROVIDED"
    AVAILABLE = "AVAILABLE"


class StateEnumerationStatus(StrEnum):
    NOT_EVALUATED = "NOT_EVALUATED"
    CERTIFIED_EXHAUSTIVE = "CERTIFIED_EXHAUSTIVE"
    CERTIFICATION_FAILED = "CERTIFICATION_FAILED"


class FeatureConclusionStatus(StrEnum):
    PRESENT_ACROSS_ALL_MODELED_STATES = "PRESENT_ACROSS_ALL_MODELED_STATES"
    POSSIBLE_IN_SOME_MODELED_STATES = "POSSIBLE_IN_SOME_MODELED_STATES"
    EXCLUDED_WITHIN_MODELED_STATE_SPACE = "EXCLUDED_WITHIN_MODELED_STATE_SPACE"
    NOT_EVALUABLE = "NOT_EVALUABLE"


class AcidBaseStateCode(StrEnum):
    ACIDEMIA = "ACIDEMIA"
    NEAR_NORMAL = "NEAR_NORMAL"
    ALKALEMIA = "ALKALEMIA"


class PrimaryProcessCode(StrEnum):
    METABOLIC_ACIDOSIS = "METABOLIC_ACIDOSIS"
    RESPIRATORY_ACIDOSIS = "RESPIRATORY_ACIDOSIS"
    METABOLIC_ALKALOSIS = "METABOLIC_ALKALOSIS"
    RESPIRATORY_ALKALOSIS = "RESPIRATORY_ALKALOSIS"
    ACIDEMIA_UNCLEAR = "ACIDEMIA_UNCLEAR"
    ALKALEMIA_UNCLEAR = "ALKALEMIA_UNCLEAR"
    NEAR_NORMAL_RESPIRATORY_ACIDOSIS_OR_MIXED = "NEAR_NORMAL_RESPIRATORY_ACIDOSIS_OR_MIXED"
    NEAR_NORMAL_RESPIRATORY_ALKALOSIS_OR_MIXED = "NEAR_NORMAL_RESPIRATORY_ALKALOSIS_OR_MIXED"
    NEAR_NORMAL_COMPENSATED_OR_MIXED = "NEAR_NORMAL_COMPENSATED_OR_MIXED"
    NO_CLEAR_PRIMARY_PROCESS = "NO_CLEAR_PRIMARY_PROCESS"


class ExpectedCompensationCode(StrEnum):
    WINTERS_PACO2_RANGE = "WINTERS_PACO2_RANGE"
    METABOLIC_ALKALOSIS_PACO2_RANGE = "METABOLIC_ALKALOSIS_PACO2_RANGE"
    RESPIRATORY_ACIDOSIS_HCO3_GUIDES = "RESPIRATORY_ACIDOSIS_HCO3_GUIDES"
    RESPIRATORY_ALKALOSIS_HCO3_GUIDES = "RESPIRATORY_ALKALOSIS_HCO3_GUIDES"
    NOT_APPLIED = "NOT_APPLIED"


class MeasuredVsExpectedCode(StrEnum):
    BELOW_EXPECTED = "BELOW_EXPECTED"
    WITHIN_EXPECTED = "WITHIN_EXPECTED"
    ABOVE_EXPECTED = "ABOVE_EXPECTED"
    NOT_APPLIED = "NOT_APPLIED"


class ChronicityBranch(StrEnum):
    CHRONIC_FLAGGED = "CHRONIC_FLAGGED"
    NOT_CHRONIC_FLAGGED = "NOT_CHRONIC_FLAGGED"


STATE_FEATURE_IDS = (
    "ACIDEMIA",
    "NEAR_NORMAL_PH",
    "ALKALEMIA",
    *(f"PRIMARY_{process.value}" for process in PrimaryProcessCode),
    *(f"EXPECTED_COMPENSATION_{code.value}" for code in ExpectedCompensationCode),
    *(f"MEASURED_VS_EXPECTED_{code.value}" for code in MeasuredVsExpectedCode),
    "METABOLIC_ACIDOSIS_COMPONENT",
    "METABOLIC_ALKALOSIS_COMPONENT",
    "RESPIRATORY_ACIDOSIS_COMPONENT",
    "RESPIRATORY_ALKALOSIS_COMPONENT",
    "MIXED_PROCESS_FLAG",
    "CHRONIC_FLAGGED_BRANCH",
    "NOT_CHRONIC_FLAGGED_BRANCH",
)


def _finite(name: str, value: object) -> float:
    if isinstance(value, bool):
        raise ExplorerInputError(f"{name} must be a finite number, not a boolean.")
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ExplorerInputError(f"{name} must be a finite number.") from error
    if not math.isfinite(numeric):
        raise ExplorerInputError(f"{name} must be a finite number.")
    return numeric


def _positive(name: str, value: object) -> float:
    numeric = _finite(name, value)
    if numeric <= 0:
        raise ExplorerInputError(f"{name} must be greater than zero.")
    return numeric


def _nonnegative(name: str, value: object) -> float:
    numeric = _finite(name, value)
    if numeric < 0:
        raise ExplorerInputError(f"{name} must be greater than or equal to zero.")
    return numeric


def _require_enum(name: str, value: object, enum_type: type[StrEnum]) -> None:
    if not isinstance(value, enum_type):
        raise ExplorerInputError(f"{name} must be a {enum_type.__name__}.")


def _string_tuple(name: str, values: tuple[str, ...]) -> None:
    if not values or any(not isinstance(value, str) or not value for value in values):
        raise ExplorerInputError(f"{name} must contain one or more nonempty strings.")
    if len(set(values)) != len(values):
        raise ExplorerInputError(f"{name} must not contain duplicates.")


@dataclass(frozen=True, slots=True)
class SaturationInput:
    """Unit-explicit venous oxygen saturation retained with its normalized value."""

    value: float
    unit: SaturationUnit
    normalized_percentage_points: float = field(init=False)

    def __post_init__(self) -> None:
        _require_enum("unit", self.unit, SaturationUnit)
        value = _nonnegative("value", self.value)
        upper = 100.0 if self.unit is SaturationUnit.PERCENTAGE_POINTS else 1.0
        if value > upper:
            raise ExplorerInputError(f"value exceeds the allowed {self.unit.value} range.")
        normalized = value if self.unit is SaturationUnit.PERCENTAGE_POINTS else value * 100.0
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "normalized_percentage_points", normalized)

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class CurrentVbg:
    ph: float | None = None
    pco2: float | None = None
    pco2_unit: Pco2Unit | None = None
    hco3_mmol_l: float | None = None
    hco3_basis: Hco3Basis = Hco3Basis.UNKNOWN
    base_excess_mmol_l: float | None = None
    venous_o2_saturation: SaturationInput | None = None
    specimen_type: SpecimenType = SpecimenType.UNKNOWN
    draw_site: DrawSite = DrawSite.UNKNOWN

    def __post_init__(self) -> None:
        if self.ph is not None:
            object.__setattr__(self, "ph", _positive("current_vbg.ph", self.ph))
        if self.pco2 is None:
            if self.pco2_unit is not None:
                raise ExplorerInputError("current_vbg.pco2_unit requires PCO2.")
        else:
            object.__setattr__(self, "pco2", _positive("current_vbg.pco2", self.pco2))
            if self.pco2_unit is None:
                raise ExplorerInputError("current_vbg.pco2_unit is required with PCO2.")
            _require_enum("current_vbg.pco2_unit", self.pco2_unit, Pco2Unit)
        _require_enum("current_vbg.hco3_basis", self.hco3_basis, Hco3Basis)
        _require_enum("current_vbg.specimen_type", self.specimen_type, SpecimenType)
        _require_enum("current_vbg.draw_site", self.draw_site, DrawSite)
        if self.hco3_mmol_l is None:
            if self.hco3_basis is not Hco3Basis.UNKNOWN:
                raise ExplorerInputError("current_vbg.hco3_basis must be UNKNOWN without HCO3.")
        else:
            object.__setattr__(
                self,
                "hco3_mmol_l",
                _positive("current_vbg.hco3_mmol_l", self.hco3_mmol_l),
            )
            if self.hco3_basis is Hco3Basis.UNKNOWN:
                raise ExplorerInputError("current_vbg.hco3_basis is required with HCO3.")
        if self.base_excess_mmol_l is not None:
            object.__setattr__(
                self,
                "base_excess_mmol_l",
                _finite("current_vbg.base_excess_mmol_l", self.base_excess_mmol_l),
            )
        if self.venous_o2_saturation is not None and not isinstance(
            self.venous_o2_saturation, SaturationInput
        ):
            raise ExplorerInputError("current_vbg.venous_o2_saturation must be SaturationInput.")
        if sum(value is not None for value in (self.ph, self.pco2, self.hco3_mmol_l)) < 2:
            raise ExplorerInputError(
                "current_vbg requires at least two of pH, PCO2, and blood-gas HCO3."
            )

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class CurrentChemistry:
    sodium_mmol_l: float | None = None
    chloride_mmol_l: float | None = None
    serum_total_co2_mmol_l: float | None = None
    albumin_g_l: float | None = None
    lactate_mmol_l: float | None = None
    relationship_to_vbg: ChemistryTimeRelationship = ChemistryTimeRelationship.UNKNOWN

    def __post_init__(self) -> None:
        if self.sodium_mmol_l is not None:
            object.__setattr__(
                self,
                "sodium_mmol_l",
                _positive("chemistry.sodium_mmol_l", self.sodium_mmol_l),
            )
        if self.chloride_mmol_l is not None:
            object.__setattr__(
                self,
                "chloride_mmol_l",
                _positive("chemistry.chloride_mmol_l", self.chloride_mmol_l),
            )
        if self.serum_total_co2_mmol_l is not None:
            object.__setattr__(
                self,
                "serum_total_co2_mmol_l",
                _nonnegative("chemistry.serum_total_co2_mmol_l", self.serum_total_co2_mmol_l),
            )
        _require_enum(
            "chemistry.relationship_to_vbg", self.relationship_to_vbg, ChemistryTimeRelationship
        )
        if self.albumin_g_l is not None:
            object.__setattr__(
                self,
                "albumin_g_l",
                _nonnegative("chemistry.albumin_g_l", self.albumin_g_l),
            )
        if self.lactate_mmol_l is not None:
            object.__setattr__(
                self,
                "lactate_mmol_l",
                _nonnegative("chemistry.lactate_mmol_l", self.lactate_mmol_l),
            )
        if (
            self.sodium_mmol_l is not None
            and self.chloride_mmol_l is not None
            and self.serum_total_co2_mmol_l is not None
        ):
            anion_gap = self.sodium_mmol_l - self.chloride_mmol_l - self.serum_total_co2_mmol_l
            if not math.isfinite(anion_gap):
                raise ExplorerInputError("chemistry values must yield a finite anion gap.")

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class ExplorerContext:
    """Minimal context; unknown remains explicit and blocks only model-dependent claims."""

    known_poor_perfusion_or_hemodynamic_instability: TriState = TriState.UNKNOWN
    recent_major_ventilation_or_treatment_change: TriState = TriState.UNKNOWN
    material_preanalytic_concern: TriState = TriState.UNKNOWN
    supplemental_oxygen: TriState = TriState.UNKNOWN

    def __post_init__(self) -> None:
        for name in (
            "known_poor_perfusion_or_hemodynamic_instability",
            "recent_major_ventilation_or_treatment_change",
            "material_preanalytic_concern",
            "supplemental_oxygen",
        ):
            _require_enum(f"context.{name}", getattr(self, name), TriState)

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class PriorObservation:
    observation_type: PriorObservationType
    elapsed_hours: float | None = None
    ph: float | None = None
    pco2: float | None = None
    pco2_unit: Pco2Unit | None = None
    hco3_mmol_l: float | None = None
    serum_total_co2_mmol_l: float | None = None
    base_excess_mmol_l: float | None = None
    specimen_type: SpecimenType | None = None
    draw_site: DrawSite | None = None
    intervening_major_ventilation_or_treatment_change: TriState = TriState.UNKNOWN

    def __post_init__(self) -> None:
        _require_enum(
            "prior_observation.observation_type", self.observation_type, PriorObservationType
        )
        _require_enum(
            "prior_observation.intervening_major_ventilation_or_treatment_change",
            self.intervening_major_ventilation_or_treatment_change,
            TriState,
        )
        if self.elapsed_hours is not None:
            object.__setattr__(
                self,
                "elapsed_hours",
                _nonnegative("prior_observation.elapsed_hours", self.elapsed_hours),
            )
        if self.ph is not None:
            object.__setattr__(self, "ph", _positive("prior_observation.ph", self.ph))
        if self.pco2 is None:
            if self.pco2_unit is not None:
                raise ExplorerInputError("prior_observation.pco2_unit requires prior PCO2.")
        else:
            object.__setattr__(self, "pco2", _positive("prior_observation.pco2", self.pco2))
            if self.pco2_unit is None:
                raise ExplorerInputError("prior_observation.pco2_unit is required with prior PCO2.")
            _require_enum("prior_observation.pco2_unit", self.pco2_unit, Pco2Unit)
        if self.hco3_mmol_l is not None:
            object.__setattr__(
                self,
                "hco3_mmol_l",
                _positive("prior_observation.hco3_mmol_l", self.hco3_mmol_l),
            )
        if self.serum_total_co2_mmol_l is not None:
            object.__setattr__(
                self,
                "serum_total_co2_mmol_l",
                _nonnegative(
                    "prior_observation.serum_total_co2_mmol_l",
                    self.serum_total_co2_mmol_l,
                ),
            )
        if self.base_excess_mmol_l is not None:
            object.__setattr__(
                self,
                "base_excess_mmol_l",
                _finite("prior_observation.base_excess_mmol_l", self.base_excess_mmol_l),
            )
        if self.observation_type is PriorObservationType.VBG:
            if self.specimen_type is None or self.draw_site is None:
                raise ExplorerInputError(
                    "A prior VBG requires explicit specimen_type and draw_site."
                )
            _require_enum("prior_observation.specimen_type", self.specimen_type, SpecimenType)
            _require_enum("prior_observation.draw_site", self.draw_site, DrawSite)
        elif self.specimen_type is not None or self.draw_site is not None:
            raise ExplorerInputError("Prior specimen/site fields are valid only for a prior VBG.")
        if self.observation_type is PriorObservationType.SERUM_TOTAL_CO2:
            if self.serum_total_co2_mmol_l is None:
                raise ExplorerInputError(
                    "A prior serum total CO2 observation requires serum_total_co2_mmol_l."
                )
            if any(
                value is not None
                for value in (self.ph, self.pco2, self.hco3_mmol_l, self.base_excess_mmol_l)
            ):
                raise ExplorerInputError(
                    "A serum total CO2 observation must not contain gas values."
                )
        elif self.serum_total_co2_mmol_l is not None:
            raise ExplorerInputError(
                "serum_total_co2_mmol_l is valid only for a serum total CO2 observation."
            )
        elif not any(
            value is not None
            for value in (self.ph, self.pco2, self.hco3_mmol_l, self.base_excess_mmol_l)
        ):
            raise ExplorerInputError("A prior ABG or VBG requires at least one observed value.")

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class VbgExplorerRequest:
    current_vbg: CurrentVbg
    current_chemistry: CurrentChemistry = field(default_factory=CurrentChemistry)
    context: ExplorerContext = field(default_factory=ExplorerContext)
    prior_observation: PriorObservation | None = None
    schema_version: str = field(init=False, default=VBG_EXPLORER_REQUEST_SCHEMA_VERSION)

    def __post_init__(self) -> None:
        if not isinstance(self.current_vbg, CurrentVbg):
            raise ExplorerInputError("current_vbg must be CurrentVbg.")
        if not isinstance(self.current_chemistry, CurrentChemistry):
            raise ExplorerInputError("current_chemistry must be CurrentChemistry.")
        if not isinstance(self.context, ExplorerContext):
            raise ExplorerInputError("context must be ExplorerContext.")
        if self.prior_observation is not None and not isinstance(
            self.prior_observation, PriorObservation
        ):
            raise ExplorerInputError("prior_observation must be PriorObservation or None.")

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)

    @classmethod
    def from_mapping(cls, value: object) -> VbgExplorerRequest:
        """Construct the sole request contract from a strict external mapping."""

        from vbg_interpreter.mapping import request_from_mapping

        return request_from_mapping(value)  # type: ignore[arg-type]

    @classmethod
    def from_json(cls, value: str) -> VbgExplorerRequest:
        """Construct the sole request contract from duplicate-free strict JSON."""

        from vbg_interpreter.mapping import request_from_json

        return request_from_json(value)


@dataclass(frozen=True, slots=True)
class NormalizedVbg:
    ph: float | None
    pco2_input: float | None
    pco2_unit: Pco2Unit | None
    pco2_mmhg: float | None
    hco3_mmol_l: float | None
    hco3_basis: Hco3Basis
    base_excess_mmol_l: float | None
    venous_o2_saturation: SaturationInput | None
    specimen_type: SpecimenType
    draw_site: DrawSite

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class CompletedVenousGas:
    """A complete pH--PCO2--HCO3 coordinate derived from at least two inputs."""

    ph: float
    pco2_mmhg: float
    hco3_mmol_l: float
    ph_origin: GasValueOrigin
    pco2_origin: GasValueOrigin
    hco3_origin: GasValueOrigin
    hco3_ph_pco2_comparator_mmol_l: float | None = None
    hco3_discrepancy_mmol_l: float | None = None
    limitation_codes: tuple[LimitationCode, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "ph", _positive("completed_venous_gas.ph", self.ph))
        object.__setattr__(
            self,
            "pco2_mmhg",
            _positive("completed_venous_gas.pco2_mmhg", self.pco2_mmhg),
        )
        object.__setattr__(
            self,
            "hco3_mmol_l",
            _positive("completed_venous_gas.hco3_mmol_l", self.hco3_mmol_l),
        )
        for name in ("ph_origin", "pco2_origin", "hco3_origin"):
            _require_enum(f"completed_venous_gas.{name}", getattr(self, name), GasValueOrigin)
        if self.hco3_ph_pco2_comparator_mmol_l is not None:
            object.__setattr__(
                self,
                "hco3_ph_pco2_comparator_mmol_l",
                _positive(
                    "completed_venous_gas.hco3_ph_pco2_comparator_mmol_l",
                    self.hco3_ph_pco2_comparator_mmol_l,
                ),
            )
        if self.hco3_discrepancy_mmol_l is not None:
            object.__setattr__(
                self,
                "hco3_discrepancy_mmol_l",
                _finite(
                    "completed_venous_gas.hco3_discrepancy_mmol_l",
                    self.hco3_discrepancy_mmol_l,
                ),
            )
        if (self.hco3_ph_pco2_comparator_mmol_l is None) != (self.hco3_discrepancy_mmol_l is None):
            raise ExplorerInputError(
                "completed_venous_gas comparator and discrepancy must be present together."
            )
        if (
            all(
                origin is GasValueOrigin.SUPPLIED
                for origin in (self.ph_origin, self.pco2_origin, self.hco3_origin)
            )
            and self.hco3_ph_pco2_comparator_mmol_l is None
        ):
            raise ExplorerInputError(
                "Three supplied gas values require an HCO3 comparator and discrepancy."
            )
        if (
            any(
                origin is GasValueOrigin.DERIVED_HENDERSON_HASSELBALCH
                for origin in (self.ph_origin, self.pco2_origin, self.hco3_origin)
            )
            and self.hco3_ph_pco2_comparator_mmol_l is not None
        ):
            raise ExplorerInputError(
                "Derived gas coordinates must not carry an all-supplied HCO3 comparator."
            )
        if not all(isinstance(code, LimitationCode) for code in self.limitation_codes):
            raise ExplorerInputError(
                "completed_venous_gas.limitation_codes must be LimitationCode."
            )

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class VenousOrientation:
    """An intentionally descriptive venous pH orientation."""

    ph_reference_orientation: VenousOrientationCode
    limitation_codes: tuple[LimitationCode, ...] = (LimitationCode.VENOUS_ONLY_ORIENTATION,)

    def __post_init__(self) -> None:
        _require_enum(
            "venous_orientation.ph_reference_orientation",
            self.ph_reference_orientation,
            VenousOrientationCode,
        )
        if not all(isinstance(code, LimitationCode) for code in self.limitation_codes):
            raise ExplorerInputError("venous_orientation.limitation_codes must be LimitationCode.")

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class NormalizedPriorObservation:
    observation: PriorObservation
    pco2_mmhg: float | None

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class NormalizedExplorerInput:
    current_vbg: NormalizedVbg
    current_chemistry: CurrentChemistry
    context: ExplorerContext
    prior_observation: NormalizedPriorObservation | None

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class EvidenceDescriptor:
    evidence_tier: EvidenceTier
    external_validation: bool
    source_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_enum("evidence_tier", self.evidence_tier, EvidenceTier)
        if type(self.external_validation) is not bool:
            raise ExplorerInputError("external_validation must be a boolean.")
        _string_tuple("source_ids", self.source_ids)

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class CalculationMetadata:
    """Method and evidence identity for a calculated, non-measured value."""

    method_id: str
    evidence: EvidenceDescriptor

    def __post_init__(self) -> None:
        if not isinstance(self.method_id, str) or not self.method_id:
            raise ExplorerInputError("calculation_metadata.method_id must be nonempty.")
        if not isinstance(self.evidence, EvidenceDescriptor):
            raise ExplorerInputError("calculation_metadata.evidence must be EvidenceDescriptor.")

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class NumericInterval:
    lower: float
    upper: float
    profile_id: str
    label: str
    evidence_tier: EvidenceTier
    error_convention: str | None = None

    def __post_init__(self) -> None:
        lower = _positive("interval.lower", self.lower)
        upper = _positive("interval.upper", self.upper)
        if lower > upper:
            raise ExplorerInputError("interval.lower must not exceed interval.upper.")
        if not isinstance(self.profile_id, str) or not self.profile_id:
            raise ExplorerInputError("interval.profile_id must be nonempty.")
        if not isinstance(self.label, str) or not self.label:
            raise ExplorerInputError("interval.label must be nonempty.")
        _require_enum("interval.evidence_tier", self.evidence_tier, EvidenceTier)
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class CandidateArterialPoint:
    ph: float
    paco2_mmhg: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "ph", _positive("candidate.ph", self.ph))
        object.__setattr__(self, "paco2_mmhg", _positive("candidate.paco2_mmhg", self.paco2_mmhg))

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class CandidateArterialRegion:
    status: CandidateRegionStatus
    reason_codes: tuple[CandidateRegionReasonCode, ...] = ()
    point: CandidateArterialPoint | None = None
    ph_interval: NumericInterval | None = None
    paco2_interval: NumericInterval | None = None
    ph_evidence: EvidenceDescriptor | None = None
    paco2_evidence: EvidenceDescriptor | None = None
    ph_model_id: str | None = None
    paco2_model_id: str | None = None
    ph_profile_id: str | None = None
    paco2_profile_id: str | None = None
    warning_codes: tuple[CandidateRegionWarningCode, ...] = ()
    limitation_codes: tuple[LimitationCode, ...] = ()

    def __post_init__(self) -> None:
        _require_enum("candidate_region.status", self.status, CandidateRegionStatus)
        if not all(isinstance(code, CandidateRegionReasonCode) for code in self.reason_codes):
            raise ExplorerInputError(
                "candidate_region.reason_codes must contain CandidateRegionReasonCode."
            )
        if len(set(self.reason_codes)) != len(self.reason_codes):
            raise ExplorerInputError("candidate_region.reason_codes must not contain duplicates.")
        if not all(isinstance(code, CandidateRegionWarningCode) for code in self.warning_codes):
            raise ExplorerInputError(
                "candidate_region.warning_codes must contain CandidateRegionWarningCode."
            )
        if not all(isinstance(code, LimitationCode) for code in self.limitation_codes):
            raise ExplorerInputError(
                "candidate_region.limitation_codes must contain LimitationCode."
            )
        modeled_values = (
            self.point,
            self.ph_interval,
            self.paco2_interval,
        )
        component_metadata = (
            self.ph_evidence,
            self.paco2_evidence,
            self.ph_model_id,
            self.paco2_model_id,
            self.ph_profile_id,
            self.paco2_profile_id,
        )
        if self.status is CandidateRegionStatus.AVAILABLE:
            if self.reason_codes or any(
                value is None for value in modeled_values + component_metadata
            ):
                raise ExplorerInputError(
                    "An available candidate region requires a complete model payload."
                )
            if not isinstance(self.point, CandidateArterialPoint):
                raise ExplorerInputError("candidate_region.point must be CandidateArterialPoint.")
            if not isinstance(self.ph_interval, NumericInterval) or not isinstance(
                self.paco2_interval, NumericInterval
            ):
                raise ExplorerInputError("An available candidate region requires both intervals.")
            if not isinstance(self.ph_evidence, EvidenceDescriptor) or not isinstance(
                self.paco2_evidence, EvidenceDescriptor
            ):
                raise ExplorerInputError(
                    "An available candidate region requires evidence metadata."
                )
            for name in ("ph_model_id", "paco2_model_id", "ph_profile_id", "paco2_profile_id"):
                value = getattr(self, name)
                if not isinstance(value, str) or not value:
                    raise ExplorerInputError(f"An available candidate region requires {name}.")
        elif self.status is CandidateRegionStatus.MODEL_DOMAIN_REFUSAL:
            if not self.reason_codes:
                raise ExplorerInputError("A refused candidate region requires typed reasons.")
            if any(value is not None for value in modeled_values):
                raise ExplorerInputError(
                    "A refused candidate region must not carry modeled values."
                )
            if any(value is None for value in component_metadata):
                raise ExplorerInputError(
                    "A refused candidate region requires attempted component metadata."
                )
            if not isinstance(self.ph_evidence, EvidenceDescriptor) or not isinstance(
                self.paco2_evidence, EvidenceDescriptor
            ):
                raise ExplorerInputError("A refused candidate region requires evidence metadata.")
            for name in ("ph_model_id", "paco2_model_id", "ph_profile_id", "paco2_profile_id"):
                value = getattr(self, name)
                if not isinstance(value, str) or not value:
                    raise ExplorerInputError(f"A refused candidate region requires {name}.")
            if self.warning_codes or self.limitation_codes:
                raise ExplorerInputError(
                    "A refused candidate region must not carry model warnings or limitations."
                )
        else:
            if not self.reason_codes:
                raise ExplorerInputError("An unavailable candidate region requires typed reasons.")
            if any(value is not None for value in modeled_values + component_metadata):
                raise ExplorerInputError(
                    "An unavailable candidate region must not carry modeled values or metadata."
                )
            if self.warning_codes or self.limitation_codes:
                raise ExplorerInputError("An unavailable candidate region must not carry warnings.")

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class ChemistryInterpretation:
    status: ChemistryStatus
    relationship_to_vbg: ChemistryTimeRelationship
    sodium_mmol_l: float | None
    chloride_mmol_l: float | None
    serum_total_co2_mmol_l: float | None
    albumin_g_l: float | None
    lactate_mmol_l: float | None
    anion_gap_mmol_l: float | None
    corrected_anion_gap_mmol_l: float | None
    limitation_codes: tuple[LimitationCode, ...]
    stewart_partition: StewartPartitionContext
    identifiable_components: tuple[str, ...]
    nonidentifiable_components: tuple[LimitationCode, ...]
    anion_gap_metadata: CalculationMetadata | None
    corrected_anion_gap_metadata: CalculationMetadata | None

    def __post_init__(self) -> None:
        _require_enum("chemistry.status", self.status, ChemistryStatus)
        _require_enum(
            "chemistry.relationship_to_vbg",
            self.relationship_to_vbg,
            ChemistryTimeRelationship,
        )
        for name, validator in (
            ("sodium_mmol_l", _positive),
            ("chloride_mmol_l", _positive),
            ("serum_total_co2_mmol_l", _nonnegative),
            ("albumin_g_l", _nonnegative),
            ("lactate_mmol_l", _nonnegative),
        ):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, validator(f"chemistry.{name}", value))
        if self.anion_gap_mmol_l is not None:
            object.__setattr__(
                self,
                "anion_gap_mmol_l",
                _finite("chemistry.anion_gap_mmol_l", self.anion_gap_mmol_l),
            )
        if self.corrected_anion_gap_mmol_l is not None:
            object.__setattr__(
                self,
                "corrected_anion_gap_mmol_l",
                _finite(
                    "chemistry.corrected_anion_gap_mmol_l",
                    self.corrected_anion_gap_mmol_l,
                ),
            )
        if not all(isinstance(code, LimitationCode) for code in self.limitation_codes):
            raise ExplorerInputError("chemistry.limitation_codes must contain LimitationCode.")
        if self.anion_gap_mmol_l is None:
            if self.anion_gap_metadata is not None:
                raise ExplorerInputError("Missing anion gap must not carry calculation metadata.")
        elif not isinstance(self.anion_gap_metadata, CalculationMetadata):
            raise ExplorerInputError("Calculated anion gap requires calculation metadata.")
        if self.corrected_anion_gap_mmol_l is None:
            if self.corrected_anion_gap_metadata is not None:
                raise ExplorerInputError(
                    "Missing corrected anion gap must not carry calculation metadata."
                )
        elif not isinstance(self.corrected_anion_gap_metadata, CalculationMetadata):
            raise ExplorerInputError(
                "Calculated corrected anion gap requires calculation metadata."
            )
        if not isinstance(self.stewart_partition, StewartPartitionContext):
            raise ExplorerInputError("chemistry.stewart_partition must be StewartPartitionContext.")
        if any(not isinstance(value, str) or not value for value in self.identifiable_components):
            raise ExplorerInputError(
                "chemistry.identifiable_components must contain nonempty strings."
            )
        if len(set(self.identifiable_components)) != len(self.identifiable_components):
            raise ExplorerInputError(
                "chemistry.identifiable_components must not contain duplicates."
            )
        if not all(isinstance(code, LimitationCode) for code in self.nonidentifiable_components):
            raise ExplorerInputError(
                "chemistry.nonidentifiable_components must contain LimitationCode."
            )

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class StewartPartitionContext:
    """Structured upstream Stewart partition, explicitly labelled venous-basis."""

    status: StewartPartitionStatus
    basis: str | None = None
    sbe_total_mmol_l: float | None = None
    sid_reference_mmol_l: float | None = None
    sid_reference_adjusted: bool | None = None
    sbe_sid_mmol_l: float | None = None
    sbe_albumin_mmol_l: float | None = None
    sbe_unmeasured_ions_mmol_l: float | None = None
    lactate_sbe_mmol_l: float | None = None
    nonlactate_unmeasured_ions_sbe_mmol_l: float | None = None
    reconstructed_sbe_mmol_l: float | None = None
    closure_error_mmol_l: float | None = None
    offsetting_components_present: bool | None = None
    partition_metadata: CalculationMetadata | None = None
    limitation_codes: tuple[LimitationCode, ...] = ()

    def __post_init__(self) -> None:
        _require_enum("stewart_partition.status", self.status, StewartPartitionStatus)
        if not all(isinstance(code, LimitationCode) for code in self.limitation_codes):
            raise ExplorerInputError(
                "stewart_partition.limitation_codes must contain LimitationCode."
            )
        numeric_names = (
            "sbe_total_mmol_l",
            "sid_reference_mmol_l",
            "sbe_sid_mmol_l",
            "sbe_albumin_mmol_l",
            "sbe_unmeasured_ions_mmol_l",
            "lactate_sbe_mmol_l",
            "nonlactate_unmeasured_ions_sbe_mmol_l",
            "reconstructed_sbe_mmol_l",
            "closure_error_mmol_l",
        )
        if self.status is StewartPartitionStatus.COMPLETED:
            if self.basis != "VENOUS_BASIS":
                raise ExplorerInputError(
                    "A completed Stewart partition must be labelled VENOUS_BASIS."
                )
            if self.limitation_codes:
                raise ExplorerInputError(
                    "A completed Stewart partition must not carry non-evaluable reasons."
                )
            for name in numeric_names:
                value = getattr(self, name)
                if value is None:
                    if name in {
                        "lactate_sbe_mmol_l",
                        "nonlactate_unmeasured_ions_sbe_mmol_l",
                    }:
                        continue
                    raise ExplorerInputError(f"Completed Stewart partition requires {name}.")
                object.__setattr__(self, name, _finite(f"stewart_partition.{name}", value))
            if type(self.sid_reference_adjusted) is not bool:
                raise ExplorerInputError(
                    "Completed Stewart partition requires sid_reference_adjusted."
                )
            if type(self.offsetting_components_present) is not bool:
                raise ExplorerInputError(
                    "Completed Stewart partition requires offsetting_components_present."
                )
            if not isinstance(self.partition_metadata, CalculationMetadata):
                raise ExplorerInputError("Completed Stewart partition requires partition_metadata.")
        else:
            if self.basis is not None or not self.limitation_codes:
                raise ExplorerInputError(
                    "A non-completed Stewart partition requires limitations and no basis."
                )
            if any(getattr(self, name) is not None for name in numeric_names) or (
                self.sid_reference_adjusted is not None
                or self.offsetting_components_present is not None
                or self.partition_metadata is not None
            ):
                raise ExplorerInputError(
                    "A non-completed Stewart partition must not carry calculated values."
                )

    @classmethod
    def not_evaluable(cls, *codes: LimitationCode) -> StewartPartitionContext:
        return cls(status=StewartPartitionStatus.NOT_EVALUABLE, limitation_codes=codes)

    @classmethod
    def model_domain_refusal(cls, *codes: LimitationCode) -> StewartPartitionContext:
        return cls(status=StewartPartitionStatus.MODEL_DOMAIN_REFUSAL, limitation_codes=codes)

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class PriorObservationSummary:
    observation_type: PriorObservationType
    elapsed_hours: float | None
    ph: float | None
    pco2_mmhg: float | None
    hco3_mmol_l: float | None
    serum_total_co2_mmol_l: float | None
    base_excess_mmol_l: float | None
    specimen_type: SpecimenType | None
    draw_site: DrawSite | None
    intervening_major_ventilation_or_treatment_change: TriState

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class HistoricalArterialCoordinate:
    ph: float
    paco2_mmhg: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "ph", _positive("historical_arterial_coordinate.ph", self.ph))
        object.__setattr__(
            self,
            "paco2_mmhg",
            _positive("historical_arterial_coordinate.paco2_mmhg", self.paco2_mmhg),
        )

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class LongitudinalContext:
    status: LongitudinalStatus
    prior_observation: PriorObservationSummary | None
    historical_arterial_coordinate: HistoricalArterialCoordinate | None
    limitation_codes: tuple[LimitationCode, ...]

    def __post_init__(self) -> None:
        _require_enum("longitudinal_context.status", self.status, LongitudinalStatus)
        if not all(isinstance(code, LimitationCode) for code in self.limitation_codes):
            raise ExplorerInputError(
                "longitudinal_context.limitation_codes must contain LimitationCode."
            )
        if self.status is LongitudinalStatus.NOT_PROVIDED:
            if (
                self.prior_observation is not None
                or self.historical_arterial_coordinate is not None
            ):
                raise ExplorerInputError("No prior observation must not contain historical values.")
            if self.limitation_codes != (LimitationCode.PRIOR_OBSERVATION_NOT_PROVIDED,):
                raise ExplorerInputError("No prior observation requires its canonical limitation.")
        elif self.prior_observation is None:
            raise ExplorerInputError("Available longitudinal context requires a prior observation.")

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class StateSignature:
    acid_base_state: AcidBaseStateCode
    primary_process: PrimaryProcessCode
    expected_compensation: ExpectedCompensationCode
    measured_vs_expected: MeasuredVsExpectedCode
    mixed_disorder_flag: bool
    chronicity_branch: ChronicityBranch

    def __post_init__(self) -> None:
        for name, enum_type in (
            ("acid_base_state", AcidBaseStateCode),
            ("primary_process", PrimaryProcessCode),
            ("expected_compensation", ExpectedCompensationCode),
            ("measured_vs_expected", MeasuredVsExpectedCode),
            ("chronicity_branch", ChronicityBranch),
        ):
            _require_enum(f"state_signature.{name}", getattr(self, name), enum_type)
        if type(self.mixed_disorder_flag) is not bool:
            raise ExplorerInputError("state_signature.mixed_disorder_flag must be a boolean.")

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class CoordinateDisplaySample:
    """One deterministic display-only sample of the certified coordinate region.

    The samples support an accessible explanatory coordinate view.  They are not
    the inference mechanism and deliberately carry no count, area, or probability
    interpretation.
    """

    ph: float
    paco2_mmhg: float
    signatures: tuple[StateSignature, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "ph", _positive("coordinate_display_sample.ph", self.ph))
        object.__setattr__(
            self,
            "paco2_mmhg",
            _positive("coordinate_display_sample.paco2_mmhg", self.paco2_mmhg),
        )
        if not self.signatures or not all(
            isinstance(signature, StateSignature) for signature in self.signatures
        ):
            raise ExplorerInputError(
                "coordinate_display_sample.signatures must contain StateSignature."
            )

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class CoordinateStateSpaceView:
    """Deterministic explanatory samples for the pH--PaCO2 coordinate view."""

    display_grid_resolution: int
    samples: tuple[CoordinateDisplaySample, ...]

    def __post_init__(self) -> None:
        if (
            isinstance(self.display_grid_resolution, bool)
            or not isinstance(self.display_grid_resolution, int)
            or self.display_grid_resolution < 2
        ):
            raise ExplorerInputError(
                "coordinate_view.display_grid_resolution must be at least two."
            )
        if len(self.samples) != self.display_grid_resolution**2:
            raise ExplorerInputError(
                "coordinate_view.samples must match the declared square display resolution."
            )
        if not all(isinstance(sample, CoordinateDisplaySample) for sample in self.samples):
            raise ExplorerInputError(
                "coordinate_view.samples must contain CoordinateDisplaySample."
            )

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class FeatureConclusion:
    feature_id: str
    status: FeatureConclusionStatus

    def __post_init__(self) -> None:
        if not isinstance(self.feature_id, str) or not self.feature_id:
            raise ExplorerInputError("feature_id must be a nonempty string.")
        _require_enum("feature_conclusion.status", self.status, FeatureConclusionStatus)

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class StateSpaceResult:
    enumeration_status: StateEnumerationStatus
    possible_signatures: tuple[StateSignature, ...] = ()
    feature_conclusions: tuple[FeatureConclusion, ...] = ()
    modeled_point: CandidateArterialPoint | None = None
    coverage_method_id: str | None = None
    decision_surface_count: int | None = None
    terminal_path_count: int | None = None
    certification_precision_digits: int | None = None
    coordinate_view: CoordinateStateSpaceView | None = None

    def __post_init__(self) -> None:
        _require_enum(
            "state_space.enumeration_status", self.enumeration_status, StateEnumerationStatus
        )
        if not all(isinstance(signature, StateSignature) for signature in self.possible_signatures):
            raise ExplorerInputError("state_space.possible_signatures must contain StateSignature.")
        if not all(isinstance(item, FeatureConclusion) for item in self.feature_conclusions):
            raise ExplorerInputError(
                "state_space.feature_conclusions must contain FeatureConclusion."
            )
        if tuple(item.feature_id for item in self.feature_conclusions) != STATE_FEATURE_IDS:
            raise ExplorerInputError(
                "state_space.feature_conclusions must use the complete canonical feature catalog."
            )
        if self.enumeration_status is StateEnumerationStatus.CERTIFIED_EXHAUSTIVE:
            if not self.possible_signatures:
                raise ExplorerInputError(
                    "Certified enumeration requires at least one possible signature."
                )
            if self.modeled_point is None or not isinstance(
                self.modeled_point, CandidateArterialPoint
            ):
                raise ExplorerInputError("Certified enumeration requires a modeled point.")
            if not isinstance(self.coverage_method_id, str) or not self.coverage_method_id:
                raise ExplorerInputError(
                    "Certified enumeration requires a coverage method identifier."
                )
            for name in (
                "decision_surface_count",
                "terminal_path_count",
                "certification_precision_digits",
            ):
                value = getattr(self, name)
                if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                    raise ExplorerInputError(f"Certified enumeration requires positive {name}.")
            if not isinstance(self.coordinate_view, CoordinateStateSpaceView):
                raise ExplorerInputError(
                    "Certified enumeration requires a coordinate display view."
                )
        if self.enumeration_status is not StateEnumerationStatus.CERTIFIED_EXHAUSTIVE:
            if (
                self.possible_signatures
                or self.modeled_point is not None
                or self.coverage_method_id is not None
                or self.decision_surface_count is not None
                or self.terminal_path_count is not None
                or self.certification_precision_digits is not None
                or self.coordinate_view is not None
            ):
                raise ExplorerInputError(
                    "Uncertified state space must not publish a modeled-state conclusion."
                )
            if any(
                item.status is not FeatureConclusionStatus.NOT_EVALUABLE
                for item in self.feature_conclusions
            ):
                raise ExplorerInputError(
                    "Uncertified state space may publish only NOT_EVALUABLE feature statuses."
                )

    @classmethod
    def not_evaluated(cls) -> StateSpaceResult:
        return cls(
            enumeration_status=StateEnumerationStatus.NOT_EVALUATED,
            feature_conclusions=tuple(
                FeatureConclusion(
                    feature_id=feature_id,
                    status=FeatureConclusionStatus.NOT_EVALUABLE,
                )
                for feature_id in STATE_FEATURE_IDS
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class ExplorerProvenance:
    software_version: str
    candidate_region_model_id: str
    candidate_region_model_version: str
    ph_evidence: EvidenceDescriptor
    paco2_evidence: EvidenceDescriptor
    boston_ruleset_id: str

    def __post_init__(self) -> None:
        for name in (
            "software_version",
            "candidate_region_model_id",
            "candidate_region_model_version",
            "boston_ruleset_id",
        ):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ExplorerInputError(f"provenance.{name} must be nonempty.")
        if self.software_version != VERSION:
            raise ExplorerInputError("provenance.software_version must match this package release.")
        if not isinstance(self.ph_evidence, EvidenceDescriptor) or not isinstance(
            self.paco2_evidence, EvidenceDescriptor
        ):
            raise ExplorerInputError("provenance evidence must use EvidenceDescriptor.")

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class VbgExplorerResult:
    normalized_input: NormalizedExplorerInput
    observed_vbg: NormalizedVbg
    completed_venous_gas: CompletedVenousGas
    venous_orientation: VenousOrientation
    candidate_arterial_region: CandidateArterialRegion
    state_space: StateSpaceResult
    chemistry: ChemistryInterpretation
    longitudinal_context: LongitudinalContext
    limitations: tuple[LimitationCode, ...]
    information_that_would_reduce_ambiguity: tuple[InformationNeedCode, ...]
    provenance: ExplorerProvenance
    schema_version: str = field(init=False, default=VBG_EXPLORER_RESULT_SCHEMA_VERSION)

    def __post_init__(self) -> None:
        if not isinstance(self.normalized_input, NormalizedExplorerInput):
            raise ExplorerInputError("normalized_input must be NormalizedExplorerInput.")
        if self.observed_vbg != self.normalized_input.current_vbg:
            raise ExplorerInputError(
                "observed_vbg must exactly preserve normalized current VBG inputs."
            )
        if not isinstance(self.completed_venous_gas, CompletedVenousGas):
            raise ExplorerInputError("completed_venous_gas must be CompletedVenousGas.")
        if not isinstance(self.venous_orientation, VenousOrientation):
            raise ExplorerInputError("venous_orientation must be VenousOrientation.")
        if not isinstance(self.candidate_arterial_region, CandidateArterialRegion):
            raise ExplorerInputError("candidate_arterial_region must be CandidateArterialRegion.")
        if not isinstance(self.state_space, StateSpaceResult):
            raise ExplorerInputError("state_space must be StateSpaceResult.")
        if not isinstance(self.chemistry, ChemistryInterpretation):
            raise ExplorerInputError("chemistry must be ChemistryInterpretation.")
        if not isinstance(self.longitudinal_context, LongitudinalContext):
            raise ExplorerInputError("longitudinal_context must be LongitudinalContext.")
        if not all(isinstance(code, LimitationCode) for code in self.limitations):
            raise ExplorerInputError("limitations must contain LimitationCode.")
        if not all(
            isinstance(code, InformationNeedCode)
            for code in self.information_that_would_reduce_ambiguity
        ):
            raise ExplorerInputError(
                "information_that_would_reduce_ambiguity must contain InformationNeedCode."
            )
        if not isinstance(self.provenance, ExplorerProvenance):
            raise ExplorerInputError("provenance must be ExplorerProvenance.")

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


def _as_dict(value: object) -> dict[str, object]:
    converted = to_primitive(value)
    if not isinstance(converted, dict):  # pragma: no cover - internal invariant
        raise TypeError("Explorer dataclass did not serialize to an object.")
    return converted
