import { clearExplorerResult, renderExplorerResult } from "./js/explorer-rendering.js";
import { createWorkerClient } from "./js/worker-client.js";

const REQUEST_SCHEMA_VERSION = "vbg_explorer_request/2.0";
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
  includePrior: document.querySelector("#include-prior"),
  priorFields: document.querySelector("#prior-fields"),
  priorType: document.querySelector("#prior-type"),
  priorGasFields: document.querySelector("#prior-gas-fields"),
  priorVbgSourceFields: document.querySelector("#prior-vbg-source-fields"),
  priorChemistryFields: document.querySelector("#prior-chemistry-fields"),
  optionalDetails: document.querySelectorAll("details.optional-group"),
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
  refs.interpretButton.disabled = !state.engineReady || state.pendingGeneration !== null;
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

function requiredDecimalString(id, label) {
  const field = byId(id);
  const raw = field.value.trim();
  const value = Number(raw);
  if (!DECIMAL_STRING.test(raw) || !Number.isFinite(value)) {
    throw new BrowserInputError(`${label} must be a finite decimal number.`);
  }
  return raw;
}

function optionalDecimalString(id, label) {
  const raw = byId(id).value.trim();
  if (!raw) {
    return null;
  }
  const value = Number(raw);
  if (!DECIMAL_STRING.test(raw) || !Number.isFinite(value)) {
    throw new BrowserInputError(`${label} must be a finite decimal number when provided.`);
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
  if ([ph, pco2, hco3].filter((value) => value !== null).length < 2) {
    throw new BrowserInputError(
      "Provide any two of measured venous pH, PvCO2, and blood-gas HCO3.",
    );
  }
  const saturationValue = optionalDecimalString(
    "venous-saturation",
    "Venous oxygen saturation",
  );
  return {
    ph,
    pco2,
    pco2_unit: pco2 === null ? null : selectValue("current-pco2-unit"),
    hco3_mmol_l: hco3,
    hco3_basis: hco3 === null ? "UNKNOWN" : selectValue("hco3-basis"),
    base_excess_mmol_l: optionalDecimalString("base-excess", "Venous base excess"),
    venous_o2_saturation:
      saturationValue === null
        ? null
        : {
            value: saturationValue,
            unit: selectValue("venous-saturation-unit"),
          },
    specimen_type: selectValue("specimen-type"),
    draw_site: selectValue("draw-site"),
  };
}

function collectCurrentChemistry() {
  return {
    sodium_mmol_l: optionalDecimalString("sodium", "Sodium"),
    chloride_mmol_l: optionalDecimalString("chloride", "Chloride"),
    serum_total_co2_mmol_l: optionalDecimalString("serum-total-co2", "Serum total CO2"),
    albumin_g_l: optionalDecimalString("albumin", "Albumin"),
    lactate_mmol_l: optionalDecimalString("lactate", "Lactate"),
    relationship_to_vbg: selectValue("chemistry-relationship"),
  };
}

function collectContext() {
  return {
    known_poor_perfusion_or_hemodynamic_instability: selectValue("poor-perfusion"),
    recent_major_ventilation_or_treatment_change: selectValue("recent-change"),
    material_preanalytic_concern: selectValue("preanalytic-concern"),
    supplemental_oxygen: selectValue("supplemental-oxygen"),
  };
}

function collectPriorObservation() {
  if (!refs.includePrior.checked) {
    return null;
  }

  const observationType = refs.priorType.value;
  const isSerumChemistry = observationType === "SERUM_TOTAL_CO2";
  const pco2 = isSerumChemistry
    ? null
    : optionalDecimalString("prior-pco2", "Prior PCO2");
  const prior = {
    observation_type: observationType,
    elapsed_hours: optionalDecimalString("prior-elapsed-hours", "Prior elapsed time"),
    ph: isSerumChemistry ? null : optionalDecimalString("prior-ph", "Prior pH"),
    pco2,
    pco2_unit: pco2 === null ? null : selectValue("prior-pco2-unit"),
    hco3_mmol_l: isSerumChemistry
      ? null
      : optionalDecimalString("prior-hco3", "Prior HCO3"),
    serum_total_co2_mmol_l: isSerumChemistry
      ? requiredDecimalString("prior-serum-total-co2", "Prior serum total CO2")
      : null,
    base_excess_mmol_l: isSerumChemistry
      ? null
      : optionalDecimalString("prior-base-excess", "Prior base excess"),
    specimen_type: observationType === "VBG" ? selectValue("prior-specimen-type") : null,
    draw_site: observationType === "VBG" ? selectValue("prior-draw-site") : null,
    intervening_major_ventilation_or_treatment_change: selectValue(
      "prior-intervening-change",
    ),
  };

  if (
    !isSerumChemistry &&
    prior.ph === null &&
    prior.pco2 === null &&
    prior.hco3_mmol_l === null &&
    prior.base_excess_mmol_l === null
  ) {
    throw new BrowserInputError("A prior gas needs at least one observed gas value.");
  }
  return prior;
}

function collectRequest() {
  return {
    schema_version: REQUEST_SCHEMA_VERSION,
    current_vbg: collectCurrentVbg(),
    current_chemistry: collectCurrentChemistry(),
    context: collectContext(),
    prior_observation: collectPriorObservation(),
  };
}

function setConditionalFieldState(container, enabled) {
  container.hidden = !enabled;
  for (const control of container.querySelectorAll("input, select")) {
    control.disabled = !enabled;
  }
}

function syncPriorFields() {
  const included = refs.includePrior.checked;
  setConditionalFieldState(refs.priorFields, included);
  if (!included) {
    return;
  }

  const priorType = refs.priorType.value;
  const isGas = priorType === "ABG" || priorType === "VBG";
  setConditionalFieldState(refs.priorGasFields, isGas);
  setConditionalFieldState(refs.priorVbgSourceFields, priorType === "VBG");
  setConditionalFieldState(refs.priorChemistryFields, priorType === "SERUM_TOTAL_CO2");
}

function resetExplorer() {
  invalidateInterpretation();
  refs.form.reset();
  for (const details of refs.optionalDetails) {
    details.open = false;
  }
  syncPriorFields();
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
      error instanceof BrowserInputError ? error.message : "Check the Explorer input fields.";
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
      throw new Error("The interpretation result could not be displayed safely.");
    }
    setRuntimeStatus("Ready: interpretation completed in this browser.", "ready");
    announce("Interpretation complete. Results are available after the input form.");
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
    setRuntimeStatus("Error: Python interpretation engine unavailable.", "error");
    showError("The local interpretation engine could not be loaded. Retry the engine.");
    announce("The interpretation engine is unavailable. Retry is available.");
  },
});

refs.form.addEventListener("submit", handleSubmit);
refs.form.addEventListener("input", () => {
  invalidateInterpretation();
  syncPriorFields();
});
refs.resetButton.addEventListener("click", resetExplorer);
refs.retryButton.addEventListener("click", () => {
  invalidateInterpretation();
  refs.retryButton.hidden = true;
  workerClient.start();
});

syncPriorFields();
clearExplorerResult();
updateSubmitAvailability();
workerClient.start();
