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


def test_live_paco2_confirmation_uncertainty_and_refusal(page, explorer_url):
    _ready(page, explorer_url)
    page.locator("#current-pco2").fill("55")
    page.locator("#venous-saturation").fill("75")
    _submit(page)
    expect(page.locator("#arterial-content")).to_contain_text("same-sample")
    page.locator("#context-details summary").click()
    page.select_option("#saturation-same-sample", "YES")
    _submit(page)
    expect(page.locator("#arterial-content")).to_contain_text("Applicability uncertain")
    expect(page.locator("#arterial-content")).to_contain_text("51.04")
    for field, value in [
        ("specimen-type", "PERIPHERAL_VENOUS"),
        ("draw-site", "UPPER_EXTREMITY_PERIPHERAL"),
        ("poor-perfusion", "NO"),
        ("recent-change", "NO"),
        ("preanalytic-concern", "NO"),
        ("supplemental-oxygen", "NO"),
    ]:
        page.select_option("#" + field, value)
    _submit(page)
    expect(page.locator("#arterial-content")).not_to_contain_text("Applicability uncertain")
    expect(page.locator("#arterial-content")).to_contain_text("45.72–56.87")
    page.select_option("#draw-site", "FEMORAL")
    _submit(page)
    expect(page.locator("#arterial-content")).to_contain_text("outside upper-extremity")
    expect(page.locator("#arterial-content")).not_to_contain_text("51.04")


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
    page.locator("#context-details summary").click()
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
