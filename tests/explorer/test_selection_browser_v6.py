"""Synthetic v0.6 checks against the actual self-hosted Pyodide worker."""

import hashlib
from urllib.parse import urlparse

import pytest
from playwright.sync_api import expect
from test_explorer_browser import PROJECT_ROOT, _ready, _submit
from test_explorer_browser import explorer_url as explorer_url

pytestmark = pytest.mark.e2e
CAPTURES = PROJECT_ROOT / ".build/v06-review"


def capture(page, name):
    CAPTURES.mkdir(parents=True, exist_ok=True)
    page.locator("#results-panel").screenshot(path=str(CAPTURES / f"{name}.png"))


def test_default_transitions_identity_and_private_inputs(page, explorer_url):
    requests, responses = [], []
    page.context.on("request", lambda request: requests.append(request))
    page.context.on("response", lambda response: responses.append(response))
    _ready(page, explorer_url)
    expect(page.locator("#build-identity")).to_contain_text("v0.6.0 · local build, commit unbound")
    expect(page.locator("#sample-type")).to_have_value("UNKNOWN")
    page.locator("#current-ph").fill("7.32")
    page.locator("#current-pco2").fill("55")
    _submit(page)
    expect(page.locator("#estimated-plot figcaption")).to_contain_text("CO₂ 50.0")
    for saturation in ("75", "", "75"):
        page.locator("#venous-saturation").fill(saturation)
        expect(page.locator("#results-panel")).to_be_hidden()
        _submit(page)
        expect(page.locator("#estimated-plot figcaption")).to_contain_text(
            "51.0" if saturation else "50.0"
        )
        assert page.locator(".agreement-whisker").count() == (3 if saturation else 0)
    expect(page.locator("#narrative-content")).to_contain_text("sample type is unknown")
    expect(page.locator("#next-inputs")).not_to_contain_text("saturation")
    capture(page, "unknown")
    for sample in ("PERIPHERAL", "CENTRAL", "UNKNOWN"):
        page.select_option("#sample-type", sample)
        expect(page.locator("#results-panel")).to_be_hidden()
        _submit(page)
        central = sample == "CENTRAL"
        expect(page.locator("#estimated-plot figcaption")).to_contain_text(
            "50.0" if central else "51.0"
        )
        assert page.locator(".agreement-whisker").count() == (0 if central else 3)
        if central:
            expect(page.locator("#narrative-content")).to_contain_text("Central sample:")
            capture(page, "central")
        page.locator("#methods-card summary").first.click()
        expect(page.locator("#methods-content")).to_contain_text(
            "fixed paco2" if central else "farkas simplified"
        )
    # Check bytes of responses actually loaded by the page/worker against this staged checkout.
    loaded = {urlparse(r.url).path.lstrip("/"): r for r in responses}
    paths = [
        "pyodide_worker.js",
        "app.js",
        "assets/py/vbg_interpreter/selection.py",
        "assets/py/vbg_interpreter/arterial_paco2.py",
        "assets/py/vbg_interpreter/version.py",
    ]
    for name in paths:
        assert name in loaded
        if name.startswith("assets/py/"):
            # CDP may re-encode text/x-python as Windows-1252 without a charset.
            # Inspect mounted bytes used by the actual Python runtime instead.
            actual = bytes(
                page.workers[0].evaluate(
                    "async path => Array.from((await getRuntime()).FS.readFile("
                    "'/vbg_explorer_app/' + path))",
                    name,
                )
            )
        else:
            actual = loaded[name].body()
        assert (
            hashlib.sha256(actual).digest()
            == hashlib.sha256((PROJECT_ROOT / ".build/web" / name).read_bytes()).digest()
        ), name
    assert all(r.method == "GET" and r.post_data is None for r in requests)
    assert all(r.url.startswith(explorer_url) and not urlparse(r.url).query for r in requests)
    assert page.evaluate("[localStorage.length, sessionStorage.length]") == [0, 0]
    assert page.url.rstrip("/") == explorer_url


@pytest.mark.parametrize("missing", ["ph", "pco2"])
def test_chained_point_keeps_only_supplied_direction(page, explorer_url, missing):
    _ready(page, explorer_url)
    supplied = "pco2" if missing == "ph" else "ph"
    page.locator(f"#current-{supplied}").fill("55" if supplied == "pco2" else "7.32")
    page.locator("#current-hco3").fill("28.34660584599947")
    page.locator("#venous-saturation").fill("75")
    _submit(page)
    expect(page.locator("#estimated-plot figcaption")).to_contain_text("pH 7.36, CO₂ 51.0")
    expect(page.locator("#narrative-content")).to_contain_text("HH-reconstructed venous")
    assert page.locator("#known-plot .coordinate-point").count() == 0
    assert page.locator("#known-plot .direction-guide").count() == 1
    assert page.locator("#estimated-plot .coordinate-point").count() == 1
    assert page.locator(".agreement-whisker").count() == (3 if missing == "ph" else 0)
    if missing == "pco2":
        expect(page.locator("#arterial-content")).to_contain_text("not quantified")
    for width in (320, 390):
        page.set_viewport_size({"width": width, "height": 900})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.set_viewport_size({"width": 1280, "height": 900})
    page.emulate_media(forced_colors="active")
    expect(page.locator("#estimated-plot svg[role=img]")).to_be_visible()
    page.emulate_media(forced_colors="none")
    capture(page, f"chained-{missing}")
    page.locator("#methods-card summary").first.click()
    expect(page.locator("#methods-content")).to_contain_text("chained / unvalidated")
    page.locator("#reset-button").click()
    expect(page.locator("#results-panel")).to_be_hidden()
    assert page.locator(".coordinate-point").count() == 0


def test_positive_point_missing_interval_and_failed_point(page, explorer_url):
    _ready(page, explorer_url)
    page.locator("#current-ph").fill("7.32")
    page.locator("#current-pco2").fill("10")
    page.locator("#venous-saturation").fill("75")
    _submit(page)
    expect(page.locator("#estimated-plot figcaption")).to_contain_text("6.0")
    expect(page.locator("#arterial-content")).to_contain_text("nonphysical")
    expect(page.locator("#arterial-content")).to_contain_text("Robustness is not quantified")
    assert page.locator(".agreement-whisker").count() == 0
    assert float(page.locator("#estimated-plot svg").get_attribute("data-y-min")) > 0
    page.locator("#current-pco2").fill("3")
    _submit(page)
    expect(page.locator("#arterial-content")).to_contain_text("Selected method: Farkas")
    expect(page.locator("#arterial-content")).not_to_contain_text("Method: fixed −5")
    assert page.locator("#estimated-plot .coordinate-point").count() == 0


def test_warned_hco3_chain_and_direct_bicarbonates(page, explorer_url):
    _ready(page, explorer_url)
    page.locator("#current-hco3").fill("25")
    page.locator("#serum-total-co2").fill("12")
    _submit(page)
    expect(page.locator("#chemistry-content")).to_contain_text("-13.0 mmol/L")
    assert page.locator(".coordinate-point").count() == 0
    page.locator("#current-ph").fill("0.32")
    _submit(page)
    expect(page.locator("#chemistry-content")).to_contain_text("-13.0 mmol/L")
    expect(page.locator("#input-observations")).not_to_be_empty()
    for ph, co2 in (("7.32", ""), ("", "55")):
        page.locator("#current-ph").fill(ph)
        page.locator("#current-pco2").fill(co2)
        page.locator("#current-hco3").fill("120")
        _submit(page)
        expect(page.locator("#input-observations")).not_to_be_empty()
        expect(page.locator("#narrative-content")).to_contain_text(
            "Provisional gas-only interpretation:"
        )
        assert page.locator("#estimated-plot .coordinate-point").count() == 1


def test_co2_only_units_and_equal_numeric_methods(page, explorer_url):
    _ready(page, explorer_url)
    page.locator("#current-pco2").fill("55")
    page.locator("#venous-saturation").fill("75")
    _submit(page)
    expect(page.locator("#arterial-content")).to_contain_text("51.0 mmHg")
    expect(page.locator("#arterial-content")).to_contain_text(
        "Requires both available arterial estimates"
    )
    assert page.locator("#estimated-plot .coordinate-point").count() == 0
    page.locator("#current-pco2").fill("7.332730262565")
    page.select_option("#current-pco2-unit", "kPa")
    page.locator("#venous-saturation").fill("0.75")
    page.select_option("#venous-saturation-unit", "FRACTION_0_TO_1")
    _submit(page)
    expect(page.locator("#arterial-content")).to_contain_text("51.0 mmHg")
    page.locator("#venous-saturation").fill("0.7027272727272727")
    _submit(page)
    expect(page.locator("#arterial-content")).to_contain_text("50.0 mmHg")
    expect(page.locator("#arterial-content")).to_contain_text("Method: Farkas")


def test_mismatched_loaded_package_version_refuses_initialization(page, explorer_url):
    # Substitute a stale version asset into the real worker; no mock scientific result.
    page.context.route(
        "**/assets/py/vbg_interpreter/version.py",
        lambda route: route.fulfill(
            status=200, content_type="text/plain", body='VERSION = "0.5.0"\n'
        ),
    )
    page.goto(explorer_url)
    expect(page.locator("#runtime-status")).to_contain_text("Error", timeout=60000)
    expect(page.locator("#interpret-button")).to_be_disabled()


def test_footer_formats_declared_commit_identity(page, explorer_url):
    import json

    manifest = json.loads((PROJECT_ROOT / ".build/web/release-manifest.json").read_text())
    manifest.update(
        build_binding="SOURCE_COMMIT", source_commit="0123456789abcdef0123456789abcdef01234567"
    )
    page.context.route(
        "**/release-manifest.json",
        lambda route: route.fulfill(
            status=200, content_type="application/json", body=json.dumps(manifest)
        ),
    )
    _ready(page, explorer_url)
    expect(page.locator("#build-identity")).to_have_text(
        "Public research preview v0.6.0 · 0123456."
    )
