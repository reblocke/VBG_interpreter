from __future__ import annotations

import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from urllib.request import urlopen

import pytest
from playwright.sync_api import Page, expect

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUILD_SCRIPT = PROJECT_ROOT / "scripts" / "build_web.py"
WEB_BUILD_ROOT = PROJECT_ROOT / ".build" / "web"

pytestmark = pytest.mark.e2e


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_server(url: str, timeout_seconds: float = 20.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=2):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"Timed out waiting for local Explorer server at {url}.")


@pytest.fixture(scope="module")
def explorer_url() -> Iterator[str]:
    completed = subprocess.run(
        [sys.executable, str(BUILD_SCRIPT)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert WEB_BUILD_ROOT.is_dir()

    port = _free_port()
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "http.server",
            str(port),
            "--bind",
            "127.0.0.1",
            "--directory",
            str(WEB_BUILD_ROOT),
        ],
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        _wait_for_server(url)
        yield url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


MOCK_WORKER = r"""
(() => {
  class ExplorerWorker {
    constructor() {
      this.listeners = { error: [], message: [] };
      window.__explorerWorker = this;
      window.__explorerWorkerMessages = [];
    }

    addEventListener(type, listener) {
      this.listeners[type].push(listener);
    }

    postMessage(message) {
      window.__explorerWorkerMessages.push(structuredClone(message));
      if (message.type === "initialize") {
        queueMicrotask(() => {
          this.emit({ id: message.id, type: "ready", payload: { ready: true } });
        });
      }
    }

    terminate() {}

    emit(data) {
      for (const listener of this.listeners.message) {
        listener({ data });
      }
    }
  }

  window.Worker = ExplorerWorker;
  window.__resolveExplorerRequest = (index, payload) => {
    const messages = window.__explorerWorkerMessages.filter(
      (message) => message.type === "interpret",
    );
    const request = messages[index];
    if (!request) {
      throw new Error("No matching Explorer request.");
    }
    window.__explorerWorker.emit({
      id: request.id,
      type: "interpretation",
      payload,
    });
  };
})();
"""


def _open_mocked_explorer(page: Page, explorer_url: str) -> None:
    page.add_init_script(MOCK_WORKER)
    page.goto(explorer_url)
    expect(page.locator("#runtime-status")).to_contain_text("Ready")


def _result():
    from vbg_interpreter import interpret_vbg
    from vbg_interpreter.models import CurrentVbg, VbgExplorerRequest
    from vbg_interpreter.serialization import to_primitive

    return {"result": to_primitive(interpret_vbg(VbgExplorerRequest(CurrentVbg(ph=7.32))))}


def _ready(page, url):
    page.goto(url)
    expect(page.locator("#runtime-status")).to_contain_text("Ready", timeout=60000)


def _submit(page):
    page.locator("#interpret-button").click()
    expect(page.locator("#results-panel")).to_be_visible(timeout=30000)


def test_live_pyodide_singletons_progressive_chemistry_and_sbe(page, explorer_url):
    requests = []
    page.on("request", lambda req: requests.append(req))
    _ready(page, explorer_url)
    for field, value, text in [
        ("current-ph", "7.32", "7.32"),
        ("current-pco2", "55", "55"),
        ("current-hco3", "27", "27"),
        ("base-excess", "-2", "-2"),
        ("venous-saturation", "75", "75"),
    ]:
        page.locator("#reset-button").click()
        page.locator("#" + field).fill(value)
        _submit(page)
        expect(page.locator("#venous-content")).to_contain_text(text)
        expect(page.locator("#chemistry-card")).to_be_hidden()
    page.locator("#reset-button").click()
    page.locator("#current-ph").fill("7.32")
    page.locator("#current-pco2").fill("55")
    _submit(page)
    expect(page.locator("#venous-content")).to_contain_text("28.347")
    expect(page.locator("#venous-content")).to_contain_text("2.563")
    for field, value in [("sodium", "140"), ("chloride", "105"), ("serum-total-co2", "24")]:
        page.locator("#" + field).fill(value)
    _submit(page)
    expect(page.locator("#chemistry-content")).to_contain_text("11 mmol/L")
    expect(page.locator("#chemistry-content")).to_contain_text("requires albumin")
    page.locator("#albumin").fill("40")
    page.select_option("#chemistry-relationship", "SAME_CLINICAL_TIMEPOINT")
    _submit(page)
    expect(page.locator("#chemistry-content")).to_contain_text("These components reconstruct")
    expect(page.locator("#chemistry-content")).to_contain_text("37°C")
    assert page.evaluate("[localStorage.length,sessionStorage.length]") == [0, 0]
    assert all(req.method == "GET" and req.post_data is None for req in requests)
    assert all(req.url.startswith(explorer_url) for req in requests)
    assert page.url.rstrip("/") == explorer_url.rstrip("/")
    assert page.locator("#next-inputs li").count() <= 3


def test_live_fixed_estimates_farkas_and_matching_coordinate_plots(page, explorer_url):
    _ready(page, explorer_url)
    page.locator("#current-ph").fill("7.32")
    page.locator("#current-pco2").fill("55")
    _submit(page)
    expect(page.locator("#arterial-content")).to_contain_text("7.36")
    expect(page.locator("#arterial-content")).to_contain_text("50 mmHg")
    expect(page.locator("#arterial-content")).to_contain_text(
        "Provisional acid–base interpretation"
    )
    expect(page.locator("#known-plot figcaption")).to_contain_text("pH 7.32, CO₂ 55")
    expect(page.locator("#estimated-plot figcaption")).to_contain_text("pH 7.36, CO₂ 50")
    assert page.locator("#estimated-plot .agreement-whisker").count() == 0
    for attr in ("data-x-min", "data-x-max", "data-y-min", "data-y-max"):
        assert page.locator("#known-plot svg").get_attribute(attr) == page.locator(
            "#estimated-plot svg"
        ).get_attribute(attr)
    # Reference-cross coordinate mapping: [7,7.8] x [20,80], plot x=65..370/y=40..290.
    known = page.locator("#known-plot .coordinate-point")
    assert float(known.get_attribute("cx")) == pytest.approx(187)
    assert float(known.get_attribute("cy")) == pytest.approx(144.1666667)
    page.locator("#venous-saturation").fill("75")
    expect(page.locator("#results-panel")).to_be_hidden()
    _submit(page)
    expect(page.locator("#arterial-content")).to_contain_text("51.04")
    expect(page.locator("#arterial-content")).to_contain_text("41.84–59.78")
    expect(page.locator("#arterial-content")).to_contain_text("Applicability is unassessed")
    assert page.locator("#estimated-plot .agreement-whisker").count() == 3
    assert page.locator("#known-plot .agreement-whisker").count() == 0
    page.locator("#methods-card summary").first.click()
    expect(page.locator("#methods-content")).to_contain_text("0.22")
    expect(page.locator("#methods-content")).to_contain_text("+ 0.04")
    expect(page.locator("label[for=venous-saturation]")).to_contain_text(
        "Same-sample venous O₂ saturation — optional"
    )
    expect(page.locator("#methods-content")).not_to_contain_text("fixed paco2 offset")
    assert page.locator("#context-details").count() == 0
    assert page.locator(".notice").count() == 0
    assert (
        page.get_by_text(
            "Research and education only. Use synthetic values only.", exact=False
        ).count()
        == 1
    )
    page.locator("#venous-saturation").fill("")
    _submit(page)
    expect(page.locator("#estimated-plot figcaption")).to_contain_text("CO₂ 50")
    assert page.locator("#estimated-plot .agreement-whisker").count() == 0
    # kPa changes neither the measured plot coordinates nor the estimate.
    page.locator("#current-pco2").fill("7.332730262565")
    page.select_option("#current-pco2-unit", "kPa")
    _submit(page)
    expect(page.locator("#known-plot figcaption")).to_contain_text("CO₂ 55")
    page.locator("#venous-saturation").fill("101")
    page.locator("#interpret-button").click()
    expect(page.locator("#form-errors")).to_contain_text("range")
    expect(page.locator("#results-panel")).to_be_hidden()


def test_reset_and_edit_invalidate_pending_response_and_keep_decimals(page, explorer_url):
    _open_mocked_explorer(page, explorer_url)
    page.locator("#current-ph").fill("7.3200")
    page.locator("#interpret-button").click()
    assert page.evaluate("window.__explorerWorkerMessages.at(-1).input.current_vbg.ph") == "7.3200"
    page.locator("#reset-button").click()
    page.evaluate("payload => window.__resolveExplorerRequest(0,payload)", _result())
    expect(page.locator("#results-panel")).to_be_hidden()
    expect(page.locator("#current-ph")).to_be_focused()
    page.locator("#current-ph").fill("7.32")
    page.locator("#interpret-button").click()
    page.locator("#current-ph").fill("7.33")
    page.evaluate("payload => window.__resolveExplorerRequest(1,payload)", _result())
    expect(page.locator("#results-panel")).to_be_hidden()


def test_keyboard_conditional_controls_mobile_zoom_and_safe_renderer(page, explorer_url):
    _open_mocked_explorer(page, explorer_url)
    expect(page.locator("#current-pco2-unit")).to_be_hidden()
    page.keyboard.press("Tab")
    expect(page.locator(".skip-link")).to_be_focused()
    page.keyboard.press("Enter")
    expect(page.locator("#main-content")).to_be_focused()
    page.locator("#current-ph").fill("7.32")
    page.locator("#interpret-button").click()
    payload = _result()
    payload["result"]["unresolved_questions"].append(
        '<img src=x onerror="window.compromised=true">'
    )
    page.evaluate("payload => window.__resolveExplorerRequest(0,payload)", payload)
    expect(page.locator("#uncertainty-content")).to_contain_text("<img")
    assert page.locator("#results-panel img").count() == 0
    assert page.evaluate("window.compromised === undefined")
    for width in (390, 320):
        page.set_viewport_size({"width": width, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    page.evaluate("document.documentElement.style.fontSize = '200%'")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    expect(page.locator("#methods-card")).not_to_have_attribute("open", "")
    page.locator("#reset-button").click()
    expect(page.locator("#results-panel")).to_be_hidden()


def test_empty_form_invalid_input_and_unversioned_result(page, explorer_url):
    _open_mocked_explorer(page, explorer_url)
    page.locator("#interpret-button").click()
    expect(page.locator("#form-errors")).to_contain_text("at least one")
    page.locator("#current-ph").fill("NaN")
    page.locator("#interpret-button").click()
    expect(page.locator("#form-errors")).to_contain_text("finite decimal")
    page.locator("#current-ph").fill("7.32")
    page.locator("#interpret-button").click()
    page.evaluate("window.__resolveExplorerRequest(0,{result:{}})")
    expect(page.locator("#form-errors")).to_contain_text("could not be displayed safely")
    expect(page.locator("#results-panel")).to_be_hidden()


def test_complete_keyboard_cycle_and_runtime_retry(page, explorer_url):
    _open_mocked_explorer(page, explorer_url)
    order = page.evaluate("""() => Array.from(document.querySelectorAll(
        'a[href],button,input,select,summary,[tabindex]')).filter(el =>
        !el.disabled && el.tabIndex >= 0 && el.getClientRects().length &&
        (!el.closest('details:not([open])') || el.tagName === 'SUMMARY')).map((el,i) => {
            el.dataset.tabOrder = String(i); return String(i);
        })""")
    page.locator(".skip-link").focus()
    for expected in order[1:]:
        page.keyboard.press("Tab")
        expect(page.locator(":focus")).to_have_attribute("data-tab-order", expected)
        assert (
            page.locator(":focus").evaluate("el => parseFloat(getComputedStyle(el).outlineWidth)")
            >= 2
        )
    page.evaluate(
        "window.__explorerWorker.listeners.error[0]({message:'Synthetic runtime failure'})"
    )
    expect(page.locator("#retry-engine")).to_be_visible()
    expect(page.locator("#assistive-status")).to_contain_text("unavailable")
    page.locator("#retry-engine").focus()
    page.keyboard.press("Enter")
    expect(page.locator("#runtime-status")).to_contain_text("Ready")
    expect(page.locator("#retry-engine")).to_be_hidden()


def test_named_landmarks_targets_forced_colors_and_400_percent_text(page, explorer_url):
    _open_mocked_explorer(page, explorer_url)
    from vbg_interpreter import interpret_vbg
    from vbg_interpreter.models import CurrentVbg, Pco2Unit, VbgExplorerRequest

    page.locator("#current-ph").fill("7.32")
    page.locator("#interpret-button").click()
    payload = {
        "result": interpret_vbg(
            VbgExplorerRequest(CurrentVbg(ph=7.32, pco2=55, pco2_unit=Pco2Unit.MMHG))
        ).to_dict()
    }
    page.evaluate("payload => window.__resolveExplorerRequest(0,payload)", payload)
    page.emulate_media(reduced_motion="reduce", forced_colors="active")
    for element in page.locator(
        "input:visible,select:visible,button:visible,summary:visible"
    ).all():
        box = element.bounding_box()
        assert box["height"] >= 44
    assert page.evaluate(r"""() =>
        Array.from(document.querySelectorAll('[aria-labelledby]')).every(el =>
            el.getAttribute('aria-labelledby').split(/\s+/).every(id =>
                document.getElementById(id)?.textContent.trim()))""")
    page.set_viewport_size({"width": 390, "height": 844})
    page.evaluate("document.documentElement.style.fontSize = '400%'")
    for font in ("system-ui", "Verdana, sans-serif"):
        page.evaluate("font => document.documentElement.style.fontFamily = font", font)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")


@pytest.mark.parametrize("ph,co2", [(7.0, 20), (7.8, 80), (6.8, 120), (8.2, 10), (400, 1000000)])
def test_coordinate_extents_reference_cross_and_no_clipped_points(page, explorer_url, ph, co2):
    from vbg_interpreter import interpret_vbg
    from vbg_interpreter.models import CurrentVbg, Pco2Unit, VbgExplorerRequest

    _open_mocked_explorer(page, explorer_url)
    page.locator("#current-ph").fill(str(ph))
    page.locator("#interpret-button").click()
    result = interpret_vbg(VbgExplorerRequest(CurrentVbg(ph=ph, pco2=co2, pco2_unit=Pco2Unit.MMHG)))
    page.evaluate(
        "payload => window.__resolveExplorerRequest(0,payload)", {"result": result.to_dict()}
    )
    for id in ("known-plot", "estimated-plot"):
        svg = page.locator(f"#{id} svg")
        assert float(svg.get_attribute("data-x-min")) <= min(ph, 7)
        assert float(svg.get_attribute("data-x-max")) >= max(ph + 0.04, 7.8)
        assert float(svg.get_attribute("data-y-min")) <= min(co2 - 5, 20)
        assert float(svg.get_attribute("data-y-max")) >= max(co2, 80)
        assert page.locator(f"#{id} .reference-line").count() == 2
        shape = page.locator(f"#{id} .coordinate-point")
        if id == "known-plot":
            x, y = float(shape.get_attribute("cx")), float(shape.get_attribute("cy"))
        else:
            x, y = float(shape.get_attribute("x")) + 6, float(shape.get_attribute("y")) + 6
        assert 65 <= x <= 370 and 40 <= y <= 290
    for width in (390, 320):
        page.set_viewport_size({"width": width, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
