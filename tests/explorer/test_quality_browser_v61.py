"""v0.6.1 presentation and warning checks through real Pyodide."""

import pytest
from playwright.sync_api import expect
from test_explorer_browser import PROJECT_ROOT, _ready, _submit
from test_explorer_browser import explorer_url as explorer_url

pytestmark = pytest.mark.e2e


@pytest.mark.parametrize(
    "ph,co2,hco3,number",
    [("7.32", "", "270", "519.9"), ("7", "", "95", "381.2"), ("", "55", "120", "7.99")],
)
def test_warned_chains_remain_numeric_without_paired_plot(
    page, explorer_url, ph, co2, hco3, number
):
    _ready(page, explorer_url)
    for selector, value in (
        ("current-ph", ph),
        ("current-pco2", co2),
        ("current-hco3", hco3),
        ("venous-saturation", "75"),
    ):
        page.locator(f"#{selector}").fill(value)
    _submit(page)
    expect(page.locator("#arterial-content")).to_contain_text(number)
    expect(page.locator("#arterial-content .warning").first).to_be_visible()
    expect(page.locator("#narrative-content")).to_contain_text("estimated paired plot are withheld")
    expect(page.locator("#estimated-plot")).to_contain_text("Estimated paired plot withheld")
    assert page.locator("#estimated-plot .coordinate-point").count() == 0
    assert page.locator("#known-plot .coordinate-point").count() == 0
    assert page.locator("#known-plot .direction-guide").count() == 1
    expect(page.locator("#known-plot .plot-legend")).to_be_visible()
    expect(page.locator("#known-plot")).to_contain_text(
        "not a guaranteed bound or probability region"
    )
    page.set_viewport_size({"width": 320, "height": 900})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    captures = PROJECT_ROOT / ".build/v061-review"
    captures.mkdir(exist_ok=True)
    page.set_viewport_size({"width": 1280, "height": 1000})
    page.locator("#results-panel").screenshot(path=str(captures / f"warning-{hco3}.png"))
    page.locator("#reset-button").click()
    expect(page.locator("#results-panel")).to_be_hidden()
    assert page.locator(".warning").count() == 0


def test_optional_calculations_and_comparator_basis(page, explorer_url):
    _ready(page, explorer_url)
    # A VBG value remains required; lactate is the only optional chemistry input.
    page.locator("#current-ph").fill("7.32")
    page.locator("#lactate").fill("2")
    _submit(page)
    expect(page.locator("#chemistry-content")).to_contain_text("Reported Lactate")
    additional = page.locator("#chemistry-content details.additional-calculations")
    expect(additional).not_to_have_attribute("open", "")
    assert "Not calculated" not in page.locator("#chemistry-content").inner_text()
    additional.locator("summary").focus()
    page.keyboard.press("Enter")
    expect(additional).to_have_attribute("open", "")
    expect(additional).to_contain_text("Not calculated")
    page.locator("#current-hco3").fill("25")
    page.locator("#serum-total-co2").fill("12")
    _submit(page)
    expect(page.locator("#chemistry-content")).to_contain_text("BMP minus reported Blood gas HCO₃")
    assert "-13.0" in page.locator("#chemistry-content").inner_text()
    page.locator("#current-ph").fill("7.32")
    page.locator("#current-pco2").fill("55")
    _submit(page)
    expect(page.locator("#chemistry-content")).to_contain_text(
        "BMP minus HH-calculated Blood gas HCO₃"
    )
    expect(page.locator("#venous-content")).to_contain_text("Reported HCO₃")
    expect(page.locator("#venous-content")).to_contain_text("HH-calculated HCO₃")
    expect(page.locator("#estimated-plot .coordinate-point")).to_be_visible()
    page.locator("#current-hco3").fill("270")
    _submit(page)
    expect(page.locator("#estimated-plot .coordinate-point")).to_be_visible()
    assert page.locator("#arterial-content .warning").count() == 0


def test_optional_refusal_visible_when_numerical_prerequisites_exist(page, explorer_url):
    _ready(page, explorer_url)
    for selector, value in (
        ("current-ph", "7.32"),
        ("current-pco2", "55"),
        ("sodium", "140"),
        ("chloride", "105"),
        ("albumin", "40"),
    ):
        page.locator(f"#{selector}").fill(value)
    _submit(page)
    visible = page.locator("#chemistry-content").inner_text()
    assert "same clinical timepoint confirmation" in visible
    page.select_option("#chemistry-relationship", "DIFFERENT_TIMEPOINT")
    _submit(page)
    assert "different timepoint" in page.locator("#chemistry-content").inner_text()
    page.select_option("#chemistry-relationship", "SAME_CLINICAL_TIMEPOINT")
    page.select_option("#albumin-unit", "g/dL")
    page.locator("#albumin").fill("1" + "0" * 308)
    _submit(page)
    assert "outside the numerical domain" in page.locator("#chemistry-content").inner_text()
    page.locator("#current-ph").fill("")
    _submit(page)
    assert "outside the numerical domain" not in page.locator("#chemistry-content").inner_text()
