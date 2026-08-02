from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = PROJECT_ROOT / "web"
INDEX_PATH = WEB_ROOT / "index.html"
WORKER_PATH = WEB_ROOT / "pyodide_worker.js"
UPSTREAM_ABG_URL = "https://reblocke.github.io/stewart-light/"


class _DocumentInventory(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str]]] = []
        self.text: list[str] = []
        self.anchors: list[dict[str, object]] = []
        self._active_anchor: dict[str, object] | None = None
        self.details: list[dict[str, object]] = []
        self._active_details: list[dict[str, object]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name: value or "" for name, value in attrs}
        self.tags.append((tag, attributes))
        if tag == "a":
            self._active_anchor = {"attributes": attributes, "text": []}
        if tag == "details":
            details: dict[str, object] = {
                "attributes": attributes,
                "elements": [],
                "tags": [],
                "text": [],
            }
            self.details.append(details)
            self._active_details.append(details)
        for details in self._active_details:
            details_elements = details["elements"]
            details_tags = details["tags"]
            assert isinstance(details_elements, list)
            assert isinstance(details_tags, list)
            details_elements.append((tag, attributes))
            details_tags.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._active_anchor is not None:
            self.anchors.append(self._active_anchor)
            self._active_anchor = None
        if tag == "details" and self._active_details:
            self._active_details.pop()

    def handle_data(self, data: str) -> None:
        self.text.append(data)
        if self._active_anchor is not None:
            anchor_text = self._active_anchor["text"]
            assert isinstance(anchor_text, list)
            anchor_text.append(data)
        for details in self._active_details:
            details_text = details["text"]
            assert isinstance(details_text, list)
            details_text.append(data)


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


def _normalized_document_text() -> str:
    return " ".join(" ".join(_document_inventory().text).lower().split())


def test_explorer_is_one_research_only_vbg_surface_with_bounded_claims() -> None:
    inventory = _document_inventory()
    text = _normalized_document_text()

    assert sum(tag == "form" for tag, _ in inventory.tags) == 1
    assert "vbg acid" in text and "explorer" in text
    assert "research" in text and "educational" in text
    assert "not validated" in text or "not clinically validated" in text
    assert (
        "does not replace an abg" in text
        or "not a substitute for an abg" in text
        or "cannot replace an abg" in text
        or "replace an arterial blood gas" in text
    )
    assert (
        "does not estimate arterial oxygenation" in text
        or "no arterial oxygenation" in text
        or "arterial oxygenation is not estimated" in text
    )
    assert "diagnos" in text and ("not" in text or "no " in text)
    assert not re.search(r"\bsupported(?:_with_caution)?\b", text)


def test_explorer_links_to_the_upstream_abg_app_without_loading_it() -> None:
    matching_links = []
    for anchor in _document_inventory().anchors:
        attributes = anchor["attributes"]
        text_parts = anchor["text"]
        assert isinstance(attributes, dict)
        assert isinstance(text_parts, list)
        if attributes.get("href") == UPSTREAM_ABG_URL:
            matching_links.append((attributes, " ".join(text_parts).lower()))

    assert len(matching_links) == 1
    attributes, link_text = matching_links[0]
    assert "abg" in link_text or "arterial" in link_text
    link_rel = set(str(attributes.get("rel", "")).split())
    assert "noreferrer" in link_rel
    if attributes.get("target") == "_blank":
        assert "noopener" in link_rel


def test_optional_inputs_are_progressively_disclosed_and_not_required() -> None:
    details_groups = _document_inventory().details
    assert details_groups, "Optional Explorer inputs must be progressively disclosed."

    optional_groups = []
    for group in details_groups:
        elements = group["elements"]
        tags = group["tags"]
        text_parts = group["text"]
        assert isinstance(elements, list)
        assert isinstance(tags, list)
        assert isinstance(text_parts, list)
        text = " ".join(" ".join(text_parts).lower().split())
        if "optional" in text:
            optional_groups.append(group)
            assert "summary" in tags
            assert "input" in tags or "select" in tags
            for tag, attributes in elements:
                if tag in {"input", "select", "textarea"}:
                    assert "required" not in attributes

    assert optional_groups


def test_state_space_has_an_accessible_visual_and_equivalent_table() -> None:
    html = INDEX_PATH.read_text(encoding="utf-8")
    document_text = _normalized_document_text()
    active_source = _active_source_text()
    combined = f"{html}\n{active_source}"

    assert re.search(r"state[- ]space", combined, re.IGNORECASE)
    assert "<svg" in html or re.search(r"createElementNS\([^\n]+[\"']svg[\"']", active_source)
    assert re.search(r'<svg[^>]+role=["\']img["\']', html) or re.search(
        r"setAttribute\(\s*[\"']role[\"']\s*,\s*[\"']img[\"']\s*\)",
        active_source,
    )
    assert "aria-label" in combined or "aria-labelledby" in combined
    assert "<table" in html or re.search(r"createElement\(\s*[\"']table[\"']\s*\)", active_source)
    assert "<caption" in html or re.search(
        r"createElement\(\s*[\"']caption[\"']\s*\)", active_source
    )
    assert "scope" in combined
    assert "not a probability" in document_text
    assert "no frequency meaning" in document_text


def test_worker_exposes_one_interpretation_message_and_exact_python_adapter() -> None:
    active_source = _active_source_text()
    worker = WORKER_PATH.read_text(encoding="utf-8")

    assert re.search(
        r"from\s+vbg_interpreter\.browser_adapter\s+import\s+"
        r"interpret_browser_request_json\b",
        worker,
    )
    assert len(re.findall(r"\binterpret_browser_request_json\s*\(", worker)) == 1
    assert re.search(r"\btype\s*===\s*[\"']interpret[\"']", worker)
    assert re.search(r"requestWorker\(\s*[\"']interpret[\"']\s*,", active_source) or re.search(
        r"postMessage\(\s*\{[^}]*\btype\s*:\s*[\"']interpret[\"']",
        active_source,
        re.DOTALL,
    )

    for obsolete_message in (
        "calculate",
        "interpret-vbg",
        "preflight-vbg",
        "estimate-vbg-paco2",
    ):
        assert obsolete_message not in active_source
    assert "stewartlight.vbg.browser_adapter" not in worker


def test_browser_preserves_decimal_lexemes_for_the_strict_python_boundary() -> None:
    app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")

    assert "DECIMAL_STRING" in app
    for function_name in ("requiredDecimalString", "optionalDecimalString"):
        match = re.search(
            rf"function\s+{function_name}\s*\([^)]*\)\s*\{{(?P<body>.*?)\n\}}",
            app,
            re.DOTALL,
        )
        assert match is not None
        body = match.group("body")
        assert "Number(raw)" in body
        assert "return raw;" in body
        assert "return value;" not in body


def test_active_explorer_has_no_storage_url_state_telemetry_or_external_api() -> None:
    source = _active_source_text()
    forbidden_patterns = {
        "local storage": r"\blocalStorage\b",
        "session storage": r"\bsessionStorage\b",
        "IndexedDB": r"\bindexedDB\b",
        "cookies": r"\bdocument\.cookie\b",
        "query-string state": r"\bURLSearchParams\b|\blocation\.search\b",
        "fragment state": r"\blocation\.hash\b",
        "history state": r"\bhistory\.(?:pushState|replaceState)\b",
        "beacon telemetry": r"\bnavigator\.sendBeacon\b",
        "streaming external connection": r"\b(?:WebSocket|EventSource)\b",
        "browser console values": r"\bconsole\.(?:log|info|debug|warn|error)\s*\(",
        "analytics SDK": r"\b(?:gtag|mixpanel|amplitude)\s*\(",
    }
    for label, pattern in forbidden_patterns.items():
        assert not re.search(pattern, source), f"Active Explorer contains {label}."

    literal_external_urls = re.findall(r"[\"'](https?://[^\"']+)[\"']", source)
    assert literal_external_urls == ["http://www.w3.org/2000/svg"]

    inventory = _document_inventory()
    for tag, attributes in inventory.tags:
        resource = attributes.get("src") or (attributes.get("href") if tag == "link" else None)
        if resource:
            assert not resource.startswith(("http://", "https://", "//"))

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


def test_active_renderer_uses_dom_nodes_not_unsafe_html_parsing() -> None:
    source = _active_source_text()
    for unsafe_api in (
        ".innerHTML",
        ".outerHTML",
        "insertAdjacentHTML",
        "document.write",
        "DOMParser",
    ):
        assert unsafe_api not in source
    assert "textContent" in source or "createTextNode" in source
    assert re.search(r"render\w*(?:Generic|Structured|Value|Object|Result)", source, re.IGNORECASE)
    assert re.search(r"\bArray\.isArray\s*\(", source)
    assert re.search(r"\bObject\.(?:entries|keys)\s*\(", source)


def test_reset_and_edits_invalidate_stale_worker_responses_before_rendering() -> None:
    source = _active_source_text()

    generation_names = set(re.findall(r"\b(?:request|render|submission)?[Gg]eneration\b", source))
    assert generation_names, "Explorer must track request generations."
    assert re.search(
        r"(?:[Gg]eneration\s*(?:\+\+|\+=\s*1)|"
        r"\+\+\s*(?:request|render|submission)?[Gg]eneration)",
        source,
    )
    assert re.search(r"await\s+[^;\n]*interpret", source, re.IGNORECASE)
    assert re.search(
        r"if\s*\([^)]*(?:request|render|submission)?[Gg]eneration"
        r"[^)]*!==?[^)]*(?:request|render|submission)?[Gg]eneration[^)]*\)"
        r"\s*(?:\{\s*)?return\b",
        source,
        re.DOTALL,
    )

    reset_matches = re.finditer(
        r"(?:function\s+\w*[Rr]eset\w*\s*\([^)]*\)|"
        r"\w*[Rr]eset\w*\s*=\s*\([^)]*\)\s*=>)(?P<body>.{0,2500})",
        source,
        re.DOTALL,
    )
    reset_bodies = [match.group("body") for match in reset_matches]
    assert reset_bodies
    assert any(
        re.search(r"[Gg]eneration|invalidate", body)
        and re.search(r"\.reset\s*\(|replaceChildren\s*\(|clear", body)
        for body in reset_bodies
    )

    assert re.search(r"addEventListener\(\s*[\"'](?:input|change)[\"']", source)
