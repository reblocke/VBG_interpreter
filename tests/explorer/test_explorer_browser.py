from __future__ import annotations

import re
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlparse
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


def _fill_minimum_gas_inputs(page: Page) -> None:
    page.locator("#current-ph").fill("7.32")
    page.locator("#current-pco2").fill("55")


def _enable_eligible_candidate_modeling(page: Page) -> None:
    page.select_option("#specimen-type", "PERIPHERAL_VENOUS")
    page.select_option("#draw-site", "UPPER_EXTREMITY_PERIPHERAL")
    page.locator("#optional-current-details summary").click()
    page.locator("#venous-saturation").fill("75")
    page.select_option("#venous-saturation-unit", "PERCENTAGE_POINTS")
    page.locator("#context-details summary").click()
    page.select_option("#poor-perfusion", "NO")
    page.select_option("#recent-change", "NO")
    page.select_option("#preanalytic-concern", "NO")
    page.select_option("#supplemental-oxygen", "NO")


def _available_result(*, unsafe_marker: str | None = None) -> dict[str, object]:
    provenance: dict[str, object] = {
        "software_version": "0.2.0",
        "model": "synthetic-browser-test",
        "nested_unknown_field": {"items": ["one", "two"]},
    }
    if unsafe_marker is not None:
        provenance["display_marker"] = unsafe_marker
    return {
        "result": {
            "schema_version": "vbg_explorer_result/2.0",
            "observed_vbg": {
                "ph": 7.32,
                "pco2_input": 55,
                "pco2_unit": "mmHg",
                "pco2_mmhg": 55,
                "hco3_mmol_l": None,
                "hco3_basis": "UNKNOWN",
                "base_excess_mmol_l": None,
                "specimen_type": "PERIPHERAL_VENOUS",
                "draw_site": "UPPER_EXTREMITY_PERIPHERAL",
                "venous_o2_saturation": None,
            },
            "completed_venous_gas": {
                "ph": 7.32,
                "pco2_mmhg": 55,
                "hco3_mmol_l": 26.3,
                "ph_origin": "SUPPLIED",
                "pco2_origin": "SUPPLIED",
                "hco3_origin": "DERIVED_HENDERSON_HASSELBALCH",
                "hco3_ph_pco2_comparator_mmol_l": None,
                "hco3_discrepancy_mmol_l": None,
                "limitation_codes": [],
            },
            "venous_orientation": {
                "ph_reference_orientation": "BELOW_RULESET_REFERENCE_BAND",
                "limitation_codes": ["VENOUS_ONLY_ORIENTATION"],
            },
            "candidate_arterial_region": {
                "status": "AVAILABLE",
                "reason_codes": [],
                "warning_codes": ["GENERIC_MODEL_WITH_UNKNOWN_SPECIMEN"],
                "point": {"ph": 7.34, "paco2_mmhg": 51.0},
                "ph_interval": {"lower": 7.31, "upper": 7.37},
                "paco2_interval": {"lower": 45.7, "upper": 56.9},
                "ph_model_id": "generic_peripheral_vbg_offset_v1",
                "paco2_model_id": "generic_peripheral_vbg_offset_v1",
                "ph_profile_id": "synthetic-ph-profile",
                "paco2_profile_id": "synthetic-paco2-profile",
                "ph_evidence": {
                    "evidence_tier": "DERIVATION_ONLY",
                    "external_validation": False,
                },
                "paco2_evidence": {
                    "evidence_tier": "DERIVATION_ONLY",
                    "external_validation": False,
                },
                "limitation_codes": [
                    "GENERIC_POPULATION_OFFSET_NOT_INDIVIDUAL_CORRECTION",
                    "GENERIC_AXES_NOT_JOINTLY_VALIDATED",
                ],
            },
            "state_space": {
                "enumeration_status": "CERTIFIED_EXHAUSTIVE",
                "possible_signatures": [
                    {
                        "chronicity_branch": "NOT_CHRONIC_FLAGGED",
                        "acid_base_state": "ACIDEMIA",
                        "primary_process": "RESPIRATORY_ACIDOSIS",
                        "expected_compensation": "RESPIRATORY_ACIDOSIS_HCO3_GUIDES",
                        "measured_vs_expected": "WITHIN_EXPECTED",
                        "mixed_disorder_flag": False,
                    }
                ],
                "feature_conclusions": [
                    {
                        "feature_id": "PRIMARY_RESPIRATORY_ACIDOSIS",
                        "status": "PRESENT_ACROSS_ALL_MODELED_STATES",
                    }
                ],
                "coordinate_view": {
                    "display_grid_resolution": 2,
                    "samples": [
                        {
                            "ph": 7.37,
                            "paco2_mmhg": 45.7,
                            "signatures": [
                                {
                                    "primary_process": "RESPIRATORY_ACIDOSIS",
                                    "mixed_disorder_flag": False,
                                }
                            ],
                        }
                    ],
                },
            },
            "chemistry": {
                "status": "COMPLETED",
                "relationship_to_vbg": "SAME_CLINICAL_TIMEPOINT",
                "sodium_mmol_l": 140,
                "chloride_mmol_l": 105,
                "serum_total_co2_mmol_l": 24,
                "albumin_g_l": None,
                "lactate_mmol_l": None,
                "anion_gap_mmol_l": 11,
                "corrected_anion_gap_mmol_l": None,
                "limitation_codes": [],
                "stewart_partition": {"status": "NOT_EVALUABLE"},
                "identifiable_components": ["SERUM_ANION_GAP"],
                "nonidentifiable_components": [],
            },
            "longitudinal_context": {
                "status": "NOT_PROVIDED",
                "prior_observation": None,
                "limitation_codes": [],
            },
            "limitations": ["SYNTHETIC_TEST_LIMITATION"],
            "information_that_would_reduce_ambiguity": ["SYNTHETIC_TEST_INFORMATION"],
            "provenance": provenance,
        }
    }


def test_reset_invalidates_a_pending_response_and_preserves_decimal_strings(
    page: Page, explorer_url: str
) -> None:
    _open_mocked_explorer(page, explorer_url)
    _fill_minimum_gas_inputs(page)
    page.locator("#interpret-button").click()

    messages = page.evaluate("window.__explorerWorkerMessages")
    assert [message["type"] for message in messages] == ["initialize", "interpret"]
    request = messages[1]["input"]
    assert request["current_vbg"]["ph"] == "7.32"
    assert request["current_vbg"]["pco2"] == "55"
    assert request["schema_version"] == "vbg_explorer_request/2.0"
    assert request["current_chemistry"]["sodium_mmol_l"] is None
    assert request["current_chemistry"]["chloride_mmol_l"] is None
    assert request["current_chemistry"]["serum_total_co2_mmol_l"] is None

    page.locator("#reset-button").click()
    expect(page.locator("#current-ph")).to_have_value("")
    expect(page.locator("#results-content")).to_be_hidden()
    expect(page.locator("#results-empty")).to_be_visible()

    page.evaluate("payload => window.__resolveExplorerRequest(0, payload)", _available_result())
    page.wait_for_timeout(50)
    expect(page.locator("#results-content")).to_be_hidden()
    expect(page.locator("#generic-result")).to_be_empty()
    expect(page.locator("#interpret-button")).to_be_enabled()


@pytest.mark.parametrize(
    ("values", "expected"),
    (
        (
            {"current-ph": "7.32", "current-pco2": "55"},
            {"ph": "7.32", "pco2": "55", "hco3_mmol_l": None, "pco2_unit": "mmHg"},
        ),
        (
            {"current-ph": "7.32", "current-hco3": "26.3"},
            {"ph": "7.32", "pco2": None, "hco3_mmol_l": "26.3", "pco2_unit": None},
        ),
        (
            {"current-pco2": "55", "current-hco3": "26.3"},
            {"ph": None, "pco2": "55", "hco3_mmol_l": "26.3", "pco2_unit": "mmHg"},
        ),
    ),
)
def test_browser_accepts_each_two_of_three_gas_pairs_without_chemistry(
    page: Page,
    explorer_url: str,
    values: dict[str, str],
    expected: dict[str, str | None],
) -> None:
    _open_mocked_explorer(page, explorer_url)
    for field_id, value in values.items():
        page.locator(f"#{field_id}").fill(value)

    page.locator("#interpret-button").click()

    messages = page.evaluate("window.__explorerWorkerMessages")
    assert [message["type"] for message in messages] == ["initialize", "interpret"]
    request = messages[1]["input"]
    actual_vbg = {key: request["current_vbg"][key] for key in (*expected, "hco3_basis")}
    assert actual_vbg == {
        **expected,
        "hco3_basis": "REPORTED" if expected["hco3_mmol_l"] is not None else "UNKNOWN",
    }
    chemistry = request["current_chemistry"]
    assert {
        key: chemistry[key]
        for key in (
            "sodium_mmol_l",
            "chloride_mmol_l",
            "serum_total_co2_mmol_l",
            "albumin_g_l",
            "lactate_mmol_l",
        )
    } == {
        "sodium_mmol_l": None,
        "chloride_mmol_l": None,
        "serum_total_co2_mmol_l": None,
        "albumin_g_l": None,
        "lactate_mmol_l": None,
    }


def test_browser_rejects_less_than_two_venous_gas_values(page: Page, explorer_url: str) -> None:
    _open_mocked_explorer(page, explorer_url)
    page.locator("#current-ph").fill("7.32")

    page.locator("#interpret-button").click()

    expect(page.locator("#form-errors")).to_contain_text("Provide any two")
    messages = page.evaluate("window.__explorerWorkerMessages")
    assert [message["type"] for message in messages] == ["initialize"]


def test_accessible_state_space_and_generic_renderer_are_safe(
    page: Page, explorer_url: str
) -> None:
    _open_mocked_explorer(page, explorer_url)
    _fill_minimum_gas_inputs(page)
    page.locator("#interpret-button").click()

    unsafe_marker = '<img id="unsafe-probe" src="x">'
    page.evaluate(
        "payload => window.__resolveExplorerRequest(0, payload)",
        _available_result(unsafe_marker=unsafe_marker),
    )

    expect(page.locator("#results-content")).to_be_visible()
    expect(page.locator("#interpretation-summary")).to_contain_text("certified modelled region")
    expect(page.locator("#state-space-figure")).to_be_visible()
    expect(page.locator("#state-space-plot")).to_have_attribute("role", "img")
    expect(page.locator("#state-space-plot .plot-display-cell")).to_have_count(1)
    plot_title = page.locator("#state-space-plot-title")
    expect(plot_title).to_contain_text("Candidate arterial")
    expect(plot_title).to_contain_text("pH")
    expect(plot_title).to_contain_text("PaCO2")
    paco2_axis_label = page.locator("#state-space-plot .plot-label").filter(has_text="PaCO")
    ph_axis_label = page.locator("#state-space-plot .plot-label").filter(has_text="pH")
    expect(paco2_axis_label).to_have_count(1)
    expect(ph_axis_label).to_have_count(1)
    assert paco2_axis_label.get_attribute("transform") is None
    expect(ph_axis_label).to_have_attribute("transform", re.compile(r"rotate\(-90"))

    sample_at_lower_paco2_upper_ph = page.locator("#state-space-plot .plot-sample")
    expect(sample_at_lower_paco2_upper_ph).to_have_count(1)
    expect(sample_at_lower_paco2_upper_ph).to_have_attribute("tabindex", "0")
    expect(sample_at_lower_paco2_upper_ph).to_have_attribute(
        "aria-label", re.compile(r"Display-only sample")
    )
    expect(sample_at_lower_paco2_upper_ph.locator("title")).to_contain_text("primary process")
    sample_at_lower_paco2_upper_ph.focus()
    expect(sample_at_lower_paco2_upper_ph).to_be_focused()
    coordinates = page.evaluate(
        """() => {
          const sample = document.querySelector("#state-space-plot .plot-sample");
          const region = document.querySelector("#state-space-plot .plot-region");
          return {
            sampleX: Number(sample.getAttribute("cx")),
            sampleY: Number(sample.getAttribute("cy")),
            regionLeft: Number(region.getAttribute("x")),
            regionTop: Number(region.getAttribute("y")),
          };
        }"""
    )
    assert coordinates["sampleX"] == pytest.approx(coordinates["regionLeft"])
    assert coordinates["sampleY"] == pytest.approx(coordinates["regionTop"])
    expect(page.locator("#state-space-table caption")).to_contain_text("certified enumeration")
    expect(page.locator("#state-space-table tbody tr")).to_have_count(1)
    expect(page.locator("#state-space-table tbody tr")).to_contain_text(
        re.compile(r"respiratory acidosis", re.IGNORECASE)
    )
    expect(page.locator("#feature-conclusions")).to_contain_text(
        "Present across all modeled states"
    )
    expect(page.locator("#chemistry-result")).to_contain_text("Same Clinical Timepoint")
    expect(page.locator("#observed-result")).to_contain_text("Measured venous inputs")
    expect(page.locator("#observed-result")).to_contain_text("Completed venous gas")
    expect(page.locator("#observed-result")).to_contain_text("Derived Henderson Hasselbalch")
    expect(page.locator("#candidate-result")).to_contain_text("Best-guess arterial orientation")
    expect(page.locator("#candidate-result")).to_contain_text(
        "published study-level agreement-extrema scenario envelope"
    )

    expect(page.locator("#unsafe-probe")).to_have_count(0)
    expect(page.locator("#generic-result")).to_contain_text(
        re.compile(re.escape(unsafe_marker), re.IGNORECASE)
    )
    expect(page.locator("#generic-result")).to_contain_text("Nested Unknown Field")


def test_renderer_refuses_an_unversioned_worker_result(page: Page, explorer_url: str) -> None:
    _open_mocked_explorer(page, explorer_url)
    _fill_minimum_gas_inputs(page)
    page.locator("#interpret-button").click()

    invalid = _available_result()
    invalid["result"]["schema_version"] = "unexpected-result/1.0"  # type: ignore[index]
    page.evaluate("payload => window.__resolveExplorerRequest(0, payload)", invalid)

    expect(page.locator("#results-content")).to_be_hidden()
    expect(page.locator("#form-errors")).to_contain_text("could not be displayed safely")


def test_live_pyodide_runs_complete_then_partial_explorer_flows(
    page: Page,
    explorer_url: str,
) -> None:
    """Exercise the staged Python packages, not only a mocked worker protocol."""

    observed_requests: list[dict[str, str]] = []
    page.on(
        "request",
        lambda request: observed_requests.append(
            {
                "method": request.method,
                "url": request.url,
                "post_data": request.post_data or "",
            }
        ),
    )
    page.goto(explorer_url)
    expect(page.locator("#runtime-status")).to_contain_text("Ready", timeout=120_000)
    initial_url = page.url
    observed_requests.clear()

    sentinels = ("7.314159", "55.271828", "141.61803", "103.57721", "23.14142")
    page.locator("#current-ph").fill(sentinels[0])
    page.locator("#current-pco2").fill(sentinels[1])
    page.locator("#sodium").fill(sentinels[2])
    page.locator("#chloride").fill(sentinels[3])
    page.locator("#serum-total-co2").fill(sentinels[4])
    _enable_eligible_candidate_modeling(page)
    page.locator("#interpret-button").click()
    expect(page.locator("#results-content")).to_be_visible(timeout=120_000)
    expect(page.locator("#candidate-result")).to_contain_text("Available")
    expect(page.locator("#state-space-summary")).to_contain_text("Certified Exhaustive")
    expect(page.locator("#state-space-figure")).to_be_visible()

    page.locator("#venous-saturation").fill("")
    page.locator("#interpret-button").click()
    expect(page.locator("#candidate-result")).to_contain_text("Available")
    expect(page.locator("#candidate-result")).to_contain_text(
        "published study-level agreement-extrema scenario envelope"
    )
    expect(page.locator("#state-space-summary")).to_contain_text("Certified Exhaustive")
    expect(page.locator("#state-space-figure")).to_be_visible()

    page.locator("#reset-button").click()
    page.locator("#current-ph").fill("7.314159")
    page.locator("#current-hco3").fill("26.3")
    page.locator("#interpret-button").click()
    expect(page.locator("#results-content")).to_be_visible(timeout=120_000)
    expect(page.locator("#candidate-result")).to_contain_text("Available")
    expect(page.locator("#observed-result")).to_contain_text("Derived Henderson Hasselbalch")
    expect(page.locator("#chemistry-result")).to_contain_text("Not Provided")

    for request in observed_requests:
        assert urlparse(request["url"]).netloc == urlparse(explorer_url).netloc
        serialized_request = f"{request['url']}\n{request['post_data']}"
        assert not any(sentinel in serialized_request for sentinel in sentinels)
    assert page.url == initial_url
    current_url = urlparse(page.url)
    assert not current_url.query and not current_url.fragment
    storage = page.evaluate(
        """async () => ({
          local: Object.keys(window.localStorage),
          session: Object.keys(window.sessionStorage),
          cookie: document.cookie,
          indexedDb: (await window.indexedDB.databases()).map((database) => database.name),
        })"""
    )
    assert storage == {"local": [], "session": [], "cookie": "", "indexedDb": []}
    assert page.context.cookies(explorer_url) == []
