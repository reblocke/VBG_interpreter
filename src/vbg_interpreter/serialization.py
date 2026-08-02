"""Deterministic, value-safe JSON primitives for the explorer contracts."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import TypeVar


class ExplorerSerializationError(ValueError):
    """Raised when a browser/API payload cannot satisfy the strict contract."""


_MappingT = TypeVar("_MappingT", bound=Mapping[str, object])


def to_primitive(value: object) -> object:
    """Convert frozen explorer contracts to deterministic JSON-compatible primitives."""

    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: to_primitive(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): to_primitive(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [to_primitive(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise ExplorerSerializationError("Explorer contracts cannot serialize nonfinite numbers.")
    return value


def to_json(value: object) -> str:
    """Serialize an explorer contract with stable ordering and compact formatting."""

    return json.dumps(
        to_primitive(value), ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )


def load_json_object(value: str) -> dict[str, object]:
    """Parse a JSON object while rejecting duplicate object keys."""

    if not isinstance(value, str):
        raise ExplorerSerializationError("Explorer JSON input must be a string.")
    try:
        parsed = json.loads(value, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as error:
        raise ExplorerSerializationError("Explorer JSON input must be valid JSON.") from error
    if not isinstance(parsed, dict):
        raise ExplorerSerializationError("Explorer JSON input must be an object.")
    return parsed


def require_exact_keys(
    value: Mapping[str, object],
    expected: frozenset[str],
    *,
    path: str,
) -> _MappingT:
    """Return a mapping only when it has the exact versioned field set."""

    if not isinstance(value, Mapping):
        raise ExplorerSerializationError(f"{path} must be an object.")
    if set(value) != expected:
        raise ExplorerSerializationError(f"{path} fields do not match the explorer schema.")
    return value  # type: ignore[return-value]


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ExplorerSerializationError(
                "Explorer JSON input must not contain duplicate fields."
            )
        result[key] = value
    return result
