import {
  clearExplorerResult,
  renderExplorerResult,
} from "./js/explorer-rendering.js";
import { createWorkerClient } from "./js/worker-client.js";

const REQUEST_SCHEMA_VERSION = "vbg_explorer_request/4.0";
const DECIMAL_STRING = /^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$/;

class BrowserInputError extends Error {}

const refs = {
  form: document.querySelector("#explorer-form"),
  interpretButton: document.querySelector("#interpret-button"),
  resetButton: document.querySelector("#reset-button"),
  retryButton: document.querySelector("#retry-engine"),
  runtimeStatus: document.querySelector("#runtime-status"),
  assistiveStatus: document.querySelector("#assistive-status"),
  formErrors: document.querySelector("#form-errors"),
  resultsPanel: document.querySelector("#results-panel"),
};

const state = {
  engineReady: false,
  requestGeneration: 0,
  pendingGeneration: null,
};

function byId(id) {
  const node = document.getElementById(id);
  if (!node) {
    throw new Error("The Explorer form is incomplete.");
  }
  return node;
}

function setRuntimeStatus(message, status) {
  refs.runtimeStatus.textContent = message;
  refs.runtimeStatus.dataset.state = status;
}

function announce(message) {
  refs.assistiveStatus.textContent = "";
  window.requestAnimationFrame(() => {
    refs.assistiveStatus.textContent = message;
  });
}

function clearError() {
  refs.formErrors.textContent = "";
  refs.formErrors.hidden = true;
}

function showError(message) {
  refs.formErrors.textContent = message;
  refs.formErrors.hidden = false;
  refs.formErrors.focus?.();
}

function updateSubmitAvailability() {
  refs.interpretButton.disabled =
    !state.engineReady || state.pendingGeneration !== null;
}

function invalidateInterpretation({ clearOutput = true } = {}) {
  state.requestGeneration += 1;
  state.pendingGeneration = null;
  if (clearOutput) {
    clearExplorerResult();
  }
  clearError();
  updateSubmitAvailability();
}

function optionalDecimalString(id, label) {
  const raw = byId(id).value.trim();
  if (!raw) {
    return null;
  }
  const value = Number(raw);
  if (!DECIMAL_STRING.test(raw) || !Number.isFinite(value)) {
    throw new BrowserInputError(
      `${label} must be a finite decimal number when provided.`,
    );
  }
  return raw;
}

function selectValue(id) {
  return byId(id).value;
}

function collectCurrentVbg() {
  const ph = optionalDecimalString("current-ph", "Measured venous pH");
  const pco2 = optionalDecimalString("current-pco2", "Measured PvCO2");
  const hco3 = optionalDecimalString("current-hco3", "HCO3");
  const saturationValue = optionalDecimalString(
    "venous-saturation",
    "Venous oxygen saturation",
  );
  const baseExcess = optionalDecimalString("base-excess", "Venous base excess");
  if ([ph, pco2, hco3, baseExcess, saturationValue].every((v) => v === null)) {
    throw new BrowserInputError("Provide at least one current VBG value.");
  }
  return {
    ph,
    pco2,
    pco2_unit: pco2 === null ? null : selectValue("current-pco2-unit"),
    hco3_mmol_l: hco3,
    hco3_basis: hco3 === null ? "UNKNOWN" : selectValue("hco3-basis"),
    base_excess_mmol_l: baseExcess,
    base_excess_basis:
      baseExcess === null ? "UNKNOWN" : selectValue("base-excess-basis"),
    venous_o2_saturation:
      saturationValue === null
        ? null
        : {
            value: saturationValue,
            unit: selectValue("venous-saturation-unit"),
          },
  };
}

function collectCurrentChemistry() {
  return {
    sodium_mmol_l: optionalDecimalString("sodium", "Sodium"),
    chloride_mmol_l: optionalDecimalString("chloride", "Chloride"),
    serum_total_co2_mmol_l: optionalDecimalString(
      "serum-total-co2",
      "Serum total CO2",
    ),
    albumin_g_l: optionalDecimalString("albumin", "Albumin"),
    lactate_mmol_l: optionalDecimalString("lactate", "Lactate"),
    relationship_to_vbg: selectValue("chemistry-relationship"),
  };
}

function collectRequest() {
  return {
    schema_version: REQUEST_SCHEMA_VERSION,
    current_vbg: collectCurrentVbg(),
    current_chemistry: collectCurrentChemistry(),
  };
}

function syncConditionalFields() {
  for (const label of document.querySelectorAll("[data-requires]")) {
    const enabled = byId(label.dataset.requires).value.trim() !== "";
    label.hidden = !enabled;
    for (const control of label.querySelectorAll("select, input"))
      control.disabled = !enabled;
  }
}

function resetExplorer() {
  invalidateInterpretation();
  refs.form.reset();
  syncConditionalFields();
  announce("Explorer inputs and results reset.");
  byId("current-ph").focus();
}

async function handleSubmit(event) {
  event.preventDefault();
  clearError();

  if (!refs.form.reportValidity()) {
    announce("Check the required Explorer inputs.");
    return;
  }

  let request;
  try {
    request = collectRequest();
  } catch (error) {
    const message =
      error instanceof BrowserInputError
        ? error.message
        : "Check the Explorer input fields.";
    showError(message);
    announce(message);
    return;
  }

  const generation = ++state.requestGeneration;
  state.pendingGeneration = generation;
  updateSubmitAvailability();
  clearExplorerResult();
  setRuntimeStatus("Interpreting with the local Python engine.", "loading");
  announce("Interpretation started.");

  try {
    const response = await workerClient.interpret(request);
    if (generation !== state.requestGeneration) {
      return;
    }
    try {
      renderExplorerResult(response);
    } catch {
      clearExplorerResult();
      throw new Error(
        "The interpretation result could not be displayed safely.",
      );
    }
    setRuntimeStatus(
      "Ready: interpretation completed in this browser.",
      "ready",
    );
    announce(
      "Interpretation complete. Results are available after the input form.",
    );
    refs.resultsPanel.focus?.({ preventScroll: true });
  } catch (error) {
    if (generation !== state.requestGeneration) {
      return;
    }
    clearExplorerResult();
    const message =
      error instanceof Error && error.message
        ? error.message
        : "Interpretation could not be completed.";
    showError(message);
    setRuntimeStatus("Ready: review the input error and try again.", "ready");
    announce(message);
  } finally {
    if (state.pendingGeneration === generation) {
      state.pendingGeneration = null;
      updateSubmitAvailability();
    }
  }
}

const workerClient = createWorkerClient({
  onReady() {
    state.engineReady = true;
    state.pendingGeneration = null;
    refs.retryButton.hidden = true;
    setRuntimeStatus("Ready: Python interpretation engine loaded.", "ready");
    updateSubmitAvailability();
    announce("Python interpretation engine ready.");
  },
  onStatus(message, status) {
    setRuntimeStatus(message, status);
  },
  onError() {
    state.engineReady = false;
    invalidateInterpretation();
    refs.retryButton.hidden = false;
    setRuntimeStatus(
      "Error: Python interpretation engine unavailable.",
      "error",
    );
    showError(
      "The local interpretation engine could not be loaded. Retry the engine.",
    );
    announce("The interpretation engine is unavailable. Retry is available.");
  },
});

refs.form.addEventListener("submit", handleSubmit);
refs.form.addEventListener("input", () => {
  invalidateInterpretation();
  syncConditionalFields();
});
refs.resetButton.addEventListener("click", resetExplorer);
refs.retryButton.addEventListener("click", () => {
  invalidateInterpretation();
  refs.retryButton.hidden = true;
  workerClient.start();
});

syncConditionalFields();
clearExplorerResult();
updateSubmitAvailability();
workerClient.start();
