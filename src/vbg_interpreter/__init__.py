"""VBG Acid–Base Explorer public interpretation boundary."""

from vbg_interpreter.interpret import interpret_vbg
from vbg_interpreter.mapping import request_from_json, request_from_mapping
from vbg_interpreter.models import VbgExplorerRequest, VbgExplorerResult
from vbg_interpreter.version import VERSION as __version__

__all__ = [
    "interpret_vbg",
    "request_from_json",
    "request_from_mapping",
    "VbgExplorerRequest",
    "VbgExplorerResult",
    "__version__",
]
