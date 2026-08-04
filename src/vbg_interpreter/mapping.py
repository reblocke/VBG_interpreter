"""Strict mapping boundary for ``vbg_explorer_request/2.0``."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from vbg_interpreter.models import (
    VBG_EXPLORER_REQUEST_SCHEMA_VERSION,
    ChemistryTimeRelationship,
    CurrentChemistry,
    CurrentVbg,
    DrawSite,
    ExplorerContext,
    Hco3Basis,
    Pco2Unit,
    PriorObservation,
    PriorObservationType,
    SaturationInput,
    SaturationUnit,
    SpecimenType,
    TriState,
    VbgExplorerRequest,
)
from vbg_interpreter.serialization import (
    ExplorerSerializationError,
    load_json_object,
    require_exact_keys,
)

_DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")
_ROOT_KEYS = frozenset(
    {"schema_version", "current_vbg", "current_chemistry", "context", "prior_observation"}
)
_CURRENT_VBG_KEYS = frozenset(
    {
        "ph",
        "pco2",
        "pco2_unit",
        "hco3_mmol_l",
        "hco3_basis",
        "base_excess_mmol_l",
        "venous_o2_saturation",
        "specimen_type",
        "draw_site",
    }
)
_CHEMISTRY_KEYS = frozenset(
    {
        "sodium_mmol_l",
        "chloride_mmol_l",
        "serum_total_co2_mmol_l",
        "albumin_g_l",
        "lactate_mmol_l",
        "relationship_to_vbg",
    }
)
_CONTEXT_KEYS = frozenset(
    {
        "known_poor_perfusion_or_hemodynamic_instability",
        "recent_major_ventilation_or_treatment_change",
        "material_preanalytic_concern",
        "supplemental_oxygen",
    }
)
_SATURATION_KEYS = frozenset({"value", "unit"})
_PRIOR_KEYS = frozenset(
    {
        "observation_type",
        "elapsed_hours",
        "ph",
        "pco2",
        "pco2_unit",
        "hco3_mmol_l",
        "serum_total_co2_mmol_l",
        "base_excess_mmol_l",
        "specimen_type",
        "draw_site",
        "intervening_major_ventilation_or_treatment_change",
    }
)


def request_from_json(payload: str) -> VbgExplorerRequest:
    """Parse a duplicate-free JSON request into the single live typed contract."""

    return request_from_mapping(load_json_object(payload))


def request_from_mapping(payload: Mapping[str, object]) -> VbgExplorerRequest:
    """Build a request only when every nested object has its exact declared fields."""

    root = require_exact_keys(payload, _ROOT_KEYS, path="request")
    if root["schema_version"] != VBG_EXPLORER_REQUEST_SCHEMA_VERSION:
        raise ExplorerSerializationError(
            "schema_version must be vbg_explorer_request/2.0; no legacy migration is available."
        )
    return VbgExplorerRequest(
        current_vbg=_current_vbg(root["current_vbg"]),
        current_chemistry=_chemistry(root["current_chemistry"]),
        context=_context(root["context"]),
        prior_observation=_prior(root["prior_observation"]),
    )


def _current_vbg(value: object) -> CurrentVbg:
    data = _object(value, _CURRENT_VBG_KEYS, "current_vbg")
    saturation = data["venous_o2_saturation"]
    return CurrentVbg(
        ph=_optional_number(data["ph"], "current_vbg.ph"),
        pco2=_optional_number(data["pco2"], "current_vbg.pco2"),
        pco2_unit=_optional_enum(Pco2Unit, data["pco2_unit"], "current_vbg.pco2_unit"),
        hco3_mmol_l=_optional_number(data["hco3_mmol_l"], "current_vbg.hco3_mmol_l"),
        hco3_basis=_enum(Hco3Basis, data["hco3_basis"], "current_vbg.hco3_basis"),
        base_excess_mmol_l=_optional_number(
            data["base_excess_mmol_l"], "current_vbg.base_excess_mmol_l"
        ),
        venous_o2_saturation=None if saturation is None else _saturation(saturation),
        specimen_type=_enum(SpecimenType, data["specimen_type"], "current_vbg.specimen_type"),
        draw_site=_enum(DrawSite, data["draw_site"], "current_vbg.draw_site"),
    )


def _chemistry(value: object) -> CurrentChemistry:
    data = _object(value, _CHEMISTRY_KEYS, "current_chemistry")
    return CurrentChemistry(
        sodium_mmol_l=_optional_number(data["sodium_mmol_l"], "current_chemistry.sodium_mmol_l"),
        chloride_mmol_l=_optional_number(
            data["chloride_mmol_l"], "current_chemistry.chloride_mmol_l"
        ),
        serum_total_co2_mmol_l=_optional_number(
            data["serum_total_co2_mmol_l"], "current_chemistry.serum_total_co2_mmol_l"
        ),
        albumin_g_l=_optional_number(data["albumin_g_l"], "current_chemistry.albumin_g_l"),
        lactate_mmol_l=_optional_number(data["lactate_mmol_l"], "current_chemistry.lactate_mmol_l"),
        relationship_to_vbg=_enum(
            ChemistryTimeRelationship,
            data["relationship_to_vbg"],
            "current_chemistry.relationship_to_vbg",
        ),
    )


def _context(value: object) -> ExplorerContext:
    data = _object(value, _CONTEXT_KEYS, "context")
    return ExplorerContext(
        known_poor_perfusion_or_hemodynamic_instability=_enum(
            TriState,
            data["known_poor_perfusion_or_hemodynamic_instability"],
            "context.known_poor_perfusion_or_hemodynamic_instability",
        ),
        recent_major_ventilation_or_treatment_change=_enum(
            TriState,
            data["recent_major_ventilation_or_treatment_change"],
            "context.recent_major_ventilation_or_treatment_change",
        ),
        material_preanalytic_concern=_enum(
            TriState,
            data["material_preanalytic_concern"],
            "context.material_preanalytic_concern",
        ),
        supplemental_oxygen=_enum(
            TriState,
            data["supplemental_oxygen"],
            "context.supplemental_oxygen",
        ),
    )


def _saturation(value: object) -> SaturationInput:
    data = _object(value, _SATURATION_KEYS, "current_vbg.venous_o2_saturation")
    return SaturationInput(
        value=_number(data["value"], "current_vbg.venous_o2_saturation.value"),
        unit=_enum(
            SaturationUnit,
            data["unit"],
            "current_vbg.venous_o2_saturation.unit",
        ),
    )


def _prior(value: object) -> PriorObservation | None:
    if value is None:
        return None
    data = _object(value, _PRIOR_KEYS, "prior_observation")
    return PriorObservation(
        observation_type=_enum(
            PriorObservationType,
            data["observation_type"],
            "prior_observation.observation_type",
        ),
        elapsed_hours=_optional_number(data["elapsed_hours"], "prior_observation.elapsed_hours"),
        ph=_optional_number(data["ph"], "prior_observation.ph"),
        pco2=_optional_number(data["pco2"], "prior_observation.pco2"),
        pco2_unit=_optional_enum(Pco2Unit, data["pco2_unit"], "prior_observation.pco2_unit"),
        hco3_mmol_l=_optional_number(data["hco3_mmol_l"], "prior_observation.hco3_mmol_l"),
        serum_total_co2_mmol_l=_optional_number(
            data["serum_total_co2_mmol_l"], "prior_observation.serum_total_co2_mmol_l"
        ),
        base_excess_mmol_l=_optional_number(
            data["base_excess_mmol_l"], "prior_observation.base_excess_mmol_l"
        ),
        specimen_type=_optional_enum(
            SpecimenType,
            data["specimen_type"],
            "prior_observation.specimen_type",
        ),
        draw_site=_optional_enum(DrawSite, data["draw_site"], "prior_observation.draw_site"),
        intervening_major_ventilation_or_treatment_change=_enum(
            TriState,
            data["intervening_major_ventilation_or_treatment_change"],
            "prior_observation.intervening_major_ventilation_or_treatment_change",
        ),
    )


def _object(value: object, expected: frozenset[str], path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ExplorerSerializationError(f"{path} must be an object.")
    return require_exact_keys(value, expected, path=path)


def _number(value: object, path: str) -> float:
    if type(value) is not str or _DECIMAL.fullmatch(value) is None:
        raise ExplorerSerializationError(f"{path} must be a finite decimal string.")
    try:
        numeric = float(Decimal(value))
    except (InvalidOperation, OverflowError, ValueError) as error:
        raise ExplorerSerializationError(f"{path} must be a finite decimal string.") from error
    if not math.isfinite(numeric):
        raise ExplorerSerializationError(f"{path} must be a finite decimal string.")
    return numeric


def _optional_number(value: object, path: str) -> float | None:
    return None if value is None else _number(value, path)


def _enum(enum_type: type[StrEnum], value: object, path: str) -> StrEnum:
    if type(value) is not str:
        raise ExplorerSerializationError(f"{path} must be a recognized enum value.")
    try:
        return enum_type(value)
    except ValueError as error:
        raise ExplorerSerializationError(f"{path} must be a recognized enum value.") from error


def _optional_enum(enum_type: type[StrEnum], value: object, path: str) -> StrEnum | None:
    return None if value is None else _enum(enum_type, value, path)
