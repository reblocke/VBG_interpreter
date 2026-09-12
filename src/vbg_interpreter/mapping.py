"""Strict mapping boundary for ``vbg_explorer_request/5.0``."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from vbg_interpreter.models import (
    VBG_EXPLORER_REQUEST_SCHEMA_VERSION,
    AlbuminInput,
    AlbuminUnit,
    BaseExcessBasis,
    ChemistryTimeRelationship,
    CurrentChemistry,
    CurrentVbg,
    Hco3Basis,
    Pco2Unit,
    SampleType,
    SaturationInput,
    SaturationUnit,
    VbgExplorerRequest,
)
from vbg_interpreter.serialization import (
    ExplorerSerializationError,
    load_json_object,
    require_exact_keys,
)

_DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")
_ROOT_KEYS = frozenset({"schema_version", "current_vbg", "current_chemistry"})
_CURRENT_VBG_KEYS = frozenset(
    {
        "ph",
        "pco2",
        "pco2_unit",
        "hco3_mmol_l",
        "hco3_basis",
        "base_excess_mmol_l",
        "base_excess_basis",
        "venous_o2_saturation",
        "sample_type",
    }
)
_CHEMISTRY_KEYS = frozenset(
    {
        "sodium_mmol_l",
        "chloride_mmol_l",
        "serum_total_co2_mmol_l",
        "albumin",
        "lactate_mmol_l",
        "relationship_to_vbg",
    }
)
_SATURATION_KEYS = frozenset({"value", "unit"})


def request_from_json(payload: str) -> VbgExplorerRequest:
    """Parse a duplicate-free JSON request into the single live typed contract."""

    return request_from_mapping(load_json_object(payload))


def request_from_mapping(payload: Mapping[str, object]) -> VbgExplorerRequest:
    """Build a request only when every nested object has its exact declared fields."""

    root = require_exact_keys(payload, _ROOT_KEYS, path="request")
    if root["schema_version"] != VBG_EXPLORER_REQUEST_SCHEMA_VERSION:
        raise ExplorerSerializationError(
            "schema_version must be vbg_explorer_request/5.0; no legacy migration is available."
        )
    return VbgExplorerRequest(
        current_vbg=_current_vbg(root["current_vbg"]),
        current_chemistry=_chemistry(root["current_chemistry"]),
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
        base_excess_basis=_enum(BaseExcessBasis, data["base_excess_basis"], "base_excess_basis"),
        venous_o2_saturation=None if saturation is None else _saturation(saturation),
        sample_type=_enum(SampleType, data["sample_type"], "current_vbg.sample_type"),
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
        albumin=None if data["albumin"] is None else _albumin(data["albumin"]),
        lactate_mmol_l=_optional_number(data["lactate_mmol_l"], "current_chemistry.lactate_mmol_l"),
        relationship_to_vbg=_enum(
            ChemistryTimeRelationship,
            data["relationship_to_vbg"],
            "current_chemistry.relationship_to_vbg",
        ),
    )


def _albumin(value: object) -> AlbuminInput:
    data = _object(value, frozenset({"value", "unit"}), "current_chemistry.albumin")
    return AlbuminInput(
        _number(data["value"], "albumin.value"), _enum(AlbuminUnit, data["unit"], "albumin.unit")
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
