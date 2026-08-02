"""Plain JSON browser boundary for the one explorer request/result contract."""

from __future__ import annotations

from collections.abc import Callable

from vbg_interpreter.mapping import request_from_json
from vbg_interpreter.models import VbgExplorerRequest
from vbg_interpreter.serialization import to_json, to_primitive


def interpret_browser_request_json(payload: str) -> str:
    """Interpret one browser JSON object and return one plain JSON result object.

    The import is intentionally lazy so the strict input boundary remains usable by
    browser/client tests while the scientific interpreter is independently tested.
    """

    from vbg_interpreter.interpret import interpret_vbg

    return interpret_browser_request_json_with(payload, interpret_vbg)


def interpret_browser_request_json_with(
    payload: str,
    interpreter: Callable[[VbgExplorerRequest], object],
) -> str:
    """Run an injected interpreter after strict JSON parsing; useful for focused tests."""

    request = request_from_json(payload)
    result = interpreter(request)
    return to_json({"result": to_primitive(result)})
