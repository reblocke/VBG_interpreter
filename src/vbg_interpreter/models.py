"""Typed contracts for the single VBG Acid--Base Explorer product."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum

from vbg_interpreter.serialization import to_primitive
from vbg_interpreter.version import VERSION

VBG_EXPLORER_REQUEST_SCHEMA_VERSION = "vbg_explorer_request/3.0"
VBG_EXPLORER_RESULT_SCHEMA_VERSION = "vbg_explorer_result/3.0"


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


class BaseExcessBasis(StrEnum):
    STANDARD = "STANDARD"
    ACTUAL = "ACTUAL"
    UNKNOWN = "UNKNOWN"


class CalculationStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE_MISSING_INPUT = "UNAVAILABLE_MISSING_INPUT"
    UNAVAILABLE_OUTSIDE_SCOPE = "UNAVAILABLE_OUTSIDE_SCOPE"
    MODEL_DOMAIN_REFUSAL = "MODEL_DOMAIN_REFUSAL"


class GasValueOrigin(StrEnum):
    MEASURED_OR_REPORTED = "MEASURED_OR_REPORTED"
    CALCULATED_HENDERSON_HASSELBALCH = "CALCULATED_HENDERSON_HASSELBALCH"
    CALCULATED_VAN_SLYKE = "CALCULATED_VAN_SLYKE"


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
    base_excess_basis: BaseExcessBasis = BaseExcessBasis.UNKNOWN
    saturation_same_sample: TriState = TriState.UNKNOWN
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
        _require_enum("base_excess_basis", self.base_excess_basis, BaseExcessBasis)
        _require_enum("saturation_same_sample", self.saturation_same_sample, TriState)
        if (
            self.base_excess_mmol_l is None
            and self.base_excess_basis is not BaseExcessBasis.UNKNOWN
        ):
            raise ExplorerInputError("Base excess basis requires a reported value.")
        if (
            self.venous_o2_saturation is None
            and self.saturation_same_sample is not TriState.UNKNOWN
        ):
            raise ExplorerInputError("Same-sample confirmation requires saturation.")
        if all(
            value is None
            for value in (
                self.ph,
                self.pco2,
                self.hco3_mmol_l,
                self.base_excess_mmol_l,
                self.venous_o2_saturation,
            )
        ):
            raise ExplorerInputError("Provide at least one current VBG value.")

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
class VbgExplorerRequest:
    current_vbg: CurrentVbg
    current_chemistry: CurrentChemistry = field(default_factory=CurrentChemistry)
    context: ExplorerContext = field(default_factory=ExplorerContext)
    schema_version: str = field(default=VBG_EXPLORER_REQUEST_SCHEMA_VERSION, init=False)

    def __post_init__(self) -> None:
        for name, kind in (
            ("current_vbg", CurrentVbg),
            ("current_chemistry", CurrentChemistry),
            ("context", ExplorerContext),
        ):
            if not isinstance(getattr(self, name), kind):
                raise ExplorerInputError(f"{name} must be {kind.__name__}.")

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True, slots=True)
class Calculation:
    status: CalculationStatus
    values: dict[str, float | str]
    units: dict[str, str]
    input_origins: dict[str, str]
    output_provenance: str
    method_id: str
    evidence_tier: str
    limitations: tuple[str, ...] = ()
    missing_inputs: tuple[str, ...] = ()
    applicability: str | None = None


@dataclass(frozen=True, slots=True)
class VenousGas:
    measured_values: dict[str, object]
    calculated_values: dict[str, Calculation]
    consistency: Calculation
    ph_reference_position: str | None
    standard_base_excess: Calculation


@dataclass(frozen=True, slots=True)
class VbgExplorerResult:
    input_summary: dict[str, object]
    venous_gas: VenousGas
    chemistry: dict[str, Calculation]
    screening: dict[str, object]
    arterial_paco2_estimate: Calculation
    unresolved_questions: tuple[str, ...]
    highest_value_next_inputs: tuple[str, ...]
    methods: dict[str, object]
    schema_version: str = field(default=VBG_EXPLORER_RESULT_SCHEMA_VERSION, init=False)
    software_version: str = field(default=VERSION, init=False)

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


def _as_dict(value: object) -> dict[str, object]:
    return to_primitive(value)  # type: ignore[return-value]
