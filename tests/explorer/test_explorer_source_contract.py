from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = PROJECT_ROOT / "web"
INDEX_PATH = WEB_ROOT / "index.html"
WORKER_PATH = WEB_ROOT / "pyodide_worker.js"


class _DocumentInventory(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name: value or "" for name, value in attrs}
        self.tags.append((tag, attributes))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


def _document_inventory() -> _DocumentInventory:
    parser = _DocumentInventory()
    parser.feed(INDEX_PATH.read_text(encoding="utf-8"))
    parser.close()
    return parser


def _active_javascript() -> dict[Path, str]:
    """Return the same-origin JavaScript graph loaded from index.html."""
    index = INDEX_PATH.read_text(encoding="utf-8")
    entries = re.findall(r'<script[^>]+src=["\']([^"\']+\.js)["\']', index)
    assert entries, "The Explorer must have a same-origin JavaScript entry point."

    pending = [(WEB_ROOT / entry.removeprefix("./")).resolve() for entry in entries]
    sources: dict[Path, str] = {}
    static_import_pattern = re.compile(r"(?:from\s+|import\s*)[\"'](\.{1,2}/[^\"']+\.js)[\"']")
    dynamic_import_pattern = re.compile(r"import\s*\(\s*[\"'](\.{1,2}/[^\"']+\.js)[\"']\s*\)")

    while pending:
        path = pending.pop()
        assert path.is_relative_to(WEB_ROOT.resolve())
        assert path.is_file(), f"Active browser module does not exist: {path}"
        if path in sources:
            continue
        source = path.read_text(encoding="utf-8")
        sources[path] = source
        imports = static_import_pattern.findall(source) + dynamic_import_pattern.findall(source)
        pending.extend((path.parent / match).resolve() for match in imports)

    sources[WORKER_PATH.resolve()] = WORKER_PATH.read_text(encoding="utf-8")
    return sources


def _active_source_text() -> str:
    return "\n".join(_active_javascript().values())


def test_privacy_guards_beyond_exercised_browser_paths() -> None:
    # Browser scenarios observe requests, URLs and local/session storage; these gaps remain.
    source = _active_source_text()
    forbidden_patterns = {
        "IndexedDB": r"\bindexedDB\b",
        "cookies": r"\bdocument\.cookie\b",
        "history state": r"\bhistory\.(?:pushState|replaceState)\b",
        "browser console values": r"\bconsole\.(?:log|info|debug|warn|error)\s*\(",
    }
    for label, pattern in forbidden_patterns.items():
        assert not re.search(pattern, source), f"Active Explorer contains {label}."

    inventory = _document_inventory()
    csp_values = [
        attributes.get("content", "")
        for tag, attributes in inventory.tags
        if tag == "meta" and attributes.get("http-equiv", "").lower() == "content-security-policy"
    ]
    assert len(csp_values) == 1
    csp = csp_values[0]
    assert "default-src 'self'" in csp
    assert "connect-src 'self'" in csp
    assert "worker-src 'self'" in csp
    assert "form-action 'none'" in csp
    assert "base-uri 'none'" in csp
