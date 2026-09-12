"""Strict input/serialization boundaries retained across the breaking schema update."""

import json
from dataclasses import replace

import pytest

from vbg_interpreter.browser_adapter import interpret_browser_request_json
from vbg_interpreter.mapping import request_from_json, request_from_mapping
from vbg_interpreter.models import (
    BaseExcessBasis,
    CurrentChemistry,
    CurrentVbg,
    ExplorerInputError,
    Hco3Basis,
    Pco2Unit,
    SaturationInput,
    SaturationUnit,
    VbgExplorerRequest,
)
from vbg_interpreter.serialization import ExplorerSerializationError, to_json, to_primitive


def wire_request(request=None):
    data = to_primitive(request or VbgExplorerRequest(CurrentVbg(ph=7.32)))
    saturation = data["current_vbg"]["venous_o2_saturation"]
    if saturation:
        saturation.pop("normalized_percentage_points")

    def decimals(value):
        if isinstance(value, dict):
            return {k: decimals(v) for k, v in value.items()}
        if isinstance(value, (int, float)):
            return str(value)
        return value

    return decimals(data)


def test_strict_mapping_and_browser_adapter():
    payload = wire_request()
    assert request_from_mapping(payload).current_vbg.ph == 7.32
    response = json.loads(interpret_browser_request_json(json.dumps(payload)))
    assert response["result"]["software_version"] == "0.4.0"
    assert response["result"]["venous_gas"]["measured_values"]["ph"]["value"] == 7.32


@pytest.mark.parametrize(
    "value", [True, 7.32, "NaN", "Infinity", "1e2", " 7.32", "+7.32", "01.3", "1,2", {}, []]
)
def test_decimal_lexemes_are_not_coerced(value):
    payload = wire_request()
    payload["current_vbg"]["ph"] = value
    with pytest.raises(ExplorerSerializationError):
        request_from_mapping(payload)


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True])
def test_positive_source_fields(value):
    with pytest.raises(ExplorerInputError):
        CurrentVbg(ph=value)


def test_empty_vbg_and_chemistry_only_do_not_submit():
    with pytest.raises(ExplorerInputError):
        CurrentVbg()
    payload = wire_request()
    payload["current_vbg"]["ph"] = None
    payload["current_chemistry"]["sodium_mmol_l"] = "140"
    with pytest.raises(ExplorerInputError):
        request_from_mapping(payload)


@pytest.mark.parametrize(
    "unit,value",
    [
        (SaturationUnit.PERCENTAGE_POINTS, 101),
        (SaturationUnit.FRACTION_0_TO_1, 1.01),
        (SaturationUnit.PERCENTAGE_POINTS, -1),
    ],
)
def test_explicit_saturation_limits(unit, value):
    with pytest.raises(ExplorerInputError):
        SaturationInput(value, unit)


def test_units_and_context_types_are_explicit():
    with pytest.raises(ExplorerInputError):
        CurrentVbg(pco2=55)
    with pytest.raises(ExplorerInputError):
        SaturationInput(75, "%")
    with pytest.raises(ExplorerInputError):
        CurrentVbg(ph=7.32, base_excess_basis=BaseExcessBasis.STANDARD)
    assert CurrentVbg(base_excess_mmol_l=0).base_excess_mmol_l == 0
    assert CurrentVbg(hco3_mmol_l=24, hco3_basis=Hco3Basis.UNKNOWN).hco3_mmol_l == 24
    assert CurrentChemistry(albumin_g_l=0, lactate_mmol_l=0).albumin_g_l == 0


def test_saturation_wire_preserves_units_without_extra_confirmation():
    req = VbgExplorerRequest(
        CurrentVbg(
            pco2=7.3,
            pco2_unit=Pco2Unit.KPA,
            venous_o2_saturation=SaturationInput(0.75, SaturationUnit.FRACTION_0_TO_1),
        )
    )
    parsed = request_from_json(json.dumps(wire_request(req)))
    assert parsed == req


@pytest.mark.parametrize("location", [None, "current_vbg", "current_chemistry"])
def test_extra_fields_are_rejected(location):
    payload = wire_request()
    obj = payload if location is None else payload[location]
    obj["unexpected_field"] = None
    with pytest.raises(ExplorerSerializationError):
        request_from_mapping(payload)


def test_version_and_duplicate_key_rejection_without_migration():
    payload = wire_request()
    payload["schema_version"] = "vbg_explorer_request/2.0"
    with pytest.raises(ExplorerSerializationError):
        request_from_mapping(payload)
    with pytest.raises(ExplorerSerializationError):
        request_from_json('{"schema_version":"a","schema_version":"b"}')
    with pytest.raises(ExplorerSerializationError):
        request_from_json("[]")


def test_nonfinite_values_never_serialize():
    with pytest.raises(ExplorerSerializationError):
        to_json({"value": float("inf")})
    with pytest.raises(ExplorerInputError):
        replace(CurrentChemistry(), lactate_mmol_l=-1)


def test_documented_synthetic_wire_example_matches_public_result():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "docs/examples"
    actual = json.loads(interpret_browser_request_json((root / "request-v4.json").read_text()))[
        "result"
    ]
    assert actual == json.loads((root / "result-v4.json").read_text())
