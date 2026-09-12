import { renderCoordinatePlots } from "./coordinate-plots.js";
import { formatNumber } from "./format.js";
const SCHEMA = "vbg_explorer_result/5.0";
const LABELS = {
  ph: "Venous pH",
  gas_basis: "Gas bicarbonate basis",
  timing: "Chemistry timing",
  HH_FROM_MEASURED_PH_PVCO2: "HH from measured venous pH and PvCO₂",
  SUPPLIED_BLOOD_GAS_HCO3_COMPLETED_PAIR:
    "Supplied Blood gas HCO₃ in a completed venous pair",
  SAME_CLINICAL_TIMEPOINT: "Same clinical timepoint",
  DIFFERENT_TIMEPOINT: "Different timepoint",
  pco2: "PvCO₂",
  hco3: "Blood gas HCO₃",
  base_excess: "Reported venous base excess",
  venous_saturation: "Venous O₂ saturation",
  sbe: "Venous standard base excess",
  reported_hco3: "Reported HCO₃",
  hh_hco3: "HH-calculated HCO₃",
  reported_minus_hh: "Reported minus HH HCO₃",
  anion_gap: "Serum anion gap",
  corrected_anion_gap: "Albumin-corrected anion gap",
  sodium_chloride_difference: "Sodium–chloride difference",
  venous_stewart_partition: "Venous Stewart partition",
  sodium_mmol_l: "Sodium",
  chloride_mmol_l: "Chloride",
  serum_total_co2_mmol_l: "BMP HCO₃",
  albumin: "Albumin",
  bmp_gas_bicarbonate_comparison: "BMP and gas bicarbonate comparison",
  bmp_hco3: "BMP HCO₃",
  gas_basis_hco3: "Gas-basis HCO₃",
  bmp_minus_gas_hco3: "BMP minus gas HCO₃",
  albumin_g_l: "Albumin",
  lactate_mmol_l: "Lactate",
  total_sbe: "Total venous SBE",
  sodium_chloride_component: "Sodium–chloride component",
  albumin_component: "Albumin component",
  unmeasured_ions_component: "Residual unmeasured-ion component",
  lactate_component: "Lactate component",
  nonlactate_unmeasured_component: "Nonlactate residual component",
  reconstructed_sbe: "Reconstructed SBE",
  closure_error: "Numerical closure error",
  point: "Estimated PaCO₂",
  measured_pvco2: "Measured PvCO₂",
  saturation_percent: "Measured venous saturation",
  STANDARD: "standard",
  ACTUAL: "actual / whole-blood",
  UNKNOWN: "unknown",
  REPORTED: "reported",
  CALCULATED: "calculated",
};
function label(key) {
  return LABELS[key] || String(key).replaceAll("_", " ");
}
function node(tag, text, className) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (className) el.className = className;
  return el;
}
const number = formatNumber;
function metric(parent, name, value, unit = "") {
  const el = node("div", undefined, "metric");
  if (name) el.append(node("strong", name));
  el.append(
    node(
      "span",
      `${number(value, unit === "pH units" ? "ph" : "other")} ${unit}`.trim(),
    ),
  );
  parent.append(el);
}
function missingLabel(value) {
  return LABELS[value] || value;
}
function renderCalculation(
  parent,
  title,
  calculation,
  { showTitle = true } = {},
) {
  if (showTitle) parent.append(node("h3", title));
  if (calculation.status !== "AVAILABLE") {
    const message =
      calculation.status === "UNAVAILABLE_MISSING_INPUT"
        ? `Not calculated — requires ${calculation.missing_inputs.map(missingLabel).join(", ")}.`
        : calculation.status === "UNAVAILABLE_OUTSIDE_SCOPE"
          ? `Not calculated — ${calculation.limitations[0] || "outside the supported scope."}`
          : "Not calculated — outside the numerical domain.";
    parent.append(node("p", message, "limitation"));
    return;
  }
  const visibleKeys =
    title === "Venous Stewart partition"
      ? [
          "total_sbe",
          "sodium_chloride_component",
          "albumin_component",
          "unmeasured_ions_component",
          "lactate_component",
          "nonlactate_unmeasured_component",
        ].filter((key) => key in calculation.values)
      : Object.keys(calculation.values);
  for (const key of visibleKeys) {
    metric(
      parent,
      showTitle && visibleKeys.length === 1 ? null : label(key),
      ["gas_basis", "timing"].includes(key)
        ? label(calculation.values[key])
        : calculation.values[key],
      calculation.units[key] || "",
    );
  }
  if (calculation.output_provenance === "CALCULATED_HENDERSON_HASSELBALCH") {
    parent.append(
      node(
        "p",
        "Calculated with Henderson–Hasselbalch; remains venous and is not an independent measurement.",
        "limitation",
      ),
    );
  }
  if (title === "Venous Stewart partition") {
    parent.append(
      node(
        "p",
        "These components reconstruct the venous SBE; the residual is not a specific diagnosis.",
      ),
    );
  }
  for (const limitation of calculation.limitations) {
    if (calculation.output_provenance === "CALCULATED_HENDERSON_HASSELBALCH")
      continue;
    parent.append(node("p", limitation, "limitation"));
  }
}
function resultObject(payload) {
  const result = payload?.result;
  if (
    !result ||
    result.schema_version !== SCHEMA ||
    !result.venous_gas ||
    !result.chemistry ||
    !Array.isArray(result.unresolved_questions) ||
    !Array.isArray(result.highest_value_next_inputs)
  ) {
    throw new Error("Unexpected interpretation result schema.");
  }
  return result;
}
export function clearExplorerResult() {
  document.getElementById("results-panel").hidden = true;
  for (const id of [
    "input-observations",
    "narrative-content",
    "venous-content",
    "chemistry-content",
    "arterial-content",
    "uncertainty-content",
    "next-inputs",
    "methods-content",
    "known-plot",
    "estimated-plot",
  ]) {
    document.getElementById(id).replaceChildren();
  }
  document.getElementById("methods-card").open = false;
}
export function renderExplorerResult(payload) {
  const result = resultObject(payload);
  clearExplorerResult();
  const observations = document.getElementById("input-observations");
  for (const observation of result.input_observations)
    observations.append(node("p", observation.message, "warning"));
  const narrative = document.getElementById("narrative-content");
  narrative.append(
    node("h3", "Best guess"),
    node("p", result.narrative.best_guess),
    node("h3", "Conditional physiology"),
    node("p", result.narrative.conditional_physiology),
  );
  const gas = document.getElementById("venous-content");
  gas.append(node("h3", "Measured / reported"));
  for (const key of [
    "ph",
    "pco2",
    "hco3",
    "base_excess",
    "venous_saturation",
  ]) {
    const entry = result.venous_gas.measured_values[key];
    if (!entry) continue;
    const unit =
      entry.units === "PERCENTAGE_POINTS"
        ? "%"
        : entry.units === "FRACTION_0_TO_1"
          ? "fraction"
          : entry.units;
    metric(gas, label(key), entry.value, unit);
    if (key === "hco3" || key === "base_excess")
      gas.append(
        node("p", `Reported basis: ${label(entry.basis)}.`, "limitation"),
      );
  }
  if (result.venous_gas.ph_reference_position)
    gas.append(
      node(
        "p",
        `Measured venous pH is ${result.venous_gas.ph_reference_position} the descriptive 7.35–7.45 reference band. This is not a validated venous normal range or arterial classification.`,
        "limitation",
      ),
    );
  gas.append(node("h3", "Calculated"));
  const gasCalculations = Object.entries(result.venous_gas.calculated_values);
  for (const [key, calc] of gasCalculations.filter(
    ([, c]) => c.status !== "UNAVAILABLE_MISSING_INPUT",
  )) {
    renderCalculation(gas, label(key), calc);
  }
  if (
    gasCalculations.length &&
    gasCalculations.every(([, c]) => c.status === "UNAVAILABLE_MISSING_INPUT")
  ) {
    gas.append(
      node(
        "p",
        "Gas completion not calculated — requires any two of pH, PvCO₂, and blood-gas HCO₃.",
        "limitation",
      ),
    );
  }
  if (result.venous_gas.consistency.status === "AVAILABLE")
    renderCalculation(
      gas,
      "Numerical HCO₃ consistency",
      result.venous_gas.consistency,
    );
  renderCalculation(
    gas,
    "Venous standard base excess",
    result.venous_gas.standard_base_excess,
  );
  const sourceChemistry = result.input_summary.current_chemistry;
  const chemistry = document.getElementById("chemistry-content");
  let anyChemistry = false;
  for (const key of [
    "sodium_mmol_l",
    "chloride_mmol_l",
    "serum_total_co2_mmol_l",
    "albumin",
    "lactate_mmol_l",
  ]) {
    const value = sourceChemistry[key];
    if (key === "relationship_to_vbg" || value === null) continue;
    anyChemistry = true;
    metric(
      chemistry,
      `Reported ${label(key)}`,
      key === "albumin" ? value.value : value,
      key === "albumin" ? value.unit : "mmol/L",
    );
  }
  document.getElementById("chemistry-card").hidden = !anyChemistry;
  if (anyChemistry)
    for (const [key, calc] of Object.entries(result.chemistry))
      renderCalculation(chemistry, label(key), calc);
  const arterial = document.getElementById("arterial-content");
  const estimate = result.arterial_paco2_estimate;
  const ph = result.arterial_ph_estimate;
  renderCalculation(arterial, "Estimated arterial pH", ph);
  arterial.append(node("h3", "Estimated PaCO₂"));
  if (estimate.status === "AVAILABLE") {
    metric(arterial, null, estimate.values.point, "mmHg");
    arterial.append(
      node(
        "p",
        estimate.method_id === "farkas_simplified_93_v1"
          ? "Method: Farkas with same-sample venous saturation."
          : "Method: fixed −5 mmHg correction.",
      ),
    );
    if (Number.isFinite(estimate.values.lower))
      metric(
        arterial,
        "Population agreement range",
        `${number(estimate.values.lower)}–${number(estimate.values.upper)}`,
        "mmHg",
      );
    for (const text of estimate.limitations)
      arterial.append(node("p", text, "limitation"));
  } else
    renderCalculation(arterial, "Estimated PaCO₂", estimate, {
      showTitle: false,
    });
  renderCalculation(
    arterial,
    "Modeled arterial bicarbonate",
    result.modeled_arterial_hco3,
  );
  const provisional = result.provisional_interpretation;
  arterial.append(node("h3", "Provisional gas-only interpretation"));
  if (provisional.status === "AVAILABLE") {
    const assessment = provisional.assessment;
    arterial.append(
      node("p", assessment.primary_process_guess),
      node("p", assessment.modeled_vs_expected),
    );
    for (const note of assessment.notes.filter(
      (text) => !text.startsWith("A single blood gas"),
    ))
      arterial.append(node("p", note, "limitation"));
  } else
    arterial.append(
      node(
        "p",
        provisional.status === "UNAVAILABLE_MISSING_INPUT"
          ? "Requires both measured pH and PvCO₂ for the estimated gas interpretation."
          : provisional.status === "UNAVAILABLE_UNRELIABLE_INPUT"
            ? "Interpretation withheld because a required gas coordinate has an input sanity warning. Finite arithmetic is retained above."
            : `Interpretation unavailable: ${label(provisional.status)}.`,
        "limitation",
      ),
    );
  for (const text of provisional.limitations)
    arterial.append(node("p", text, "limitation"));
  const sensitivity = result.interpretation_sensitivity;
  arterial.append(
    node("h3", "CO₂ scenario sensitivity"),
    node("p", sensitivity.summary),
  );
  if (sensitivity.scenarios.length) {
    const details = node("details");
    details.append(node("summary", "Tested CO₂ scenarios"));
    for (const scenario of sensitivity.scenarios) {
      details.append(
        node("h3", label(scenario.name)),
        node(
          "p",
          `pH ${number(scenario.ph, "ph")}; CO₂ ${number(scenario.pco2)} mmHg; modeled HCO₃ ${number(scenario.hco3)} mmol/L.`,
        ),
        node(
          "p",
          scenario.assessment.primary_process_guess || label(scenario.status),
        ),
        node(
          "p",
          scenario.assessment.modeled_vs_expected || "Comparison unavailable.",
        ),
      );
    }
    for (const text of sensitivity.limitations)
      details.append(node("p", text, "limitation"));
    arterial.append(details);
  }
  renderCoordinatePlots(result);
  for (const text of result.unresolved_questions)
    document.getElementById("uncertainty-content").append(node("li", text));
  for (const text of result.highest_value_next_inputs)
    document.getElementById("next-inputs").append(node("li", text));
  const calculations = [
    ...Object.values(result.venous_gas.calculated_values),
    result.venous_gas.standard_base_excess,
    ...Object.values(result.chemistry),
    estimate,
    ph,
    result.modeled_arterial_hco3,
  ];
  const methods = document.getElementById("methods-content");
  methods.append(
    node(
      "p",
      "No categorical PvCO₂ screening threshold is configured. Screening, prediction, compensation classification, and management equivalence are separate claims.",
    ),
  );
  const usedMethods = new Set(
    calculations
      .filter((c) => c.status !== "UNAVAILABLE_MISSING_INPUT")
      .map((c) => c.method_id),
  );
  usedMethods.add(result.physiology_direction.model_id);
  if (result.venous_gas.consistency.status === "AVAILABLE")
    usedMethods.add(result.venous_gas.consistency.method_id);
  if (provisional.status !== "UNAVAILABLE_MISSING_INPUT")
    usedMethods.add(provisional.method_id);
  for (const [id, method] of Object.entries(result.methods).filter(([id]) =>
    usedMethods.has(id),
  )) {
    methods.append(
      node("h3", label(id)),
      node("p", method.description),
      node("p", `Evidence: ${label(method.evidence_tier)}.`, "limitation"),
    );
    for (const source of method.sources) {
      const href = source.startsWith("https://")
        ? source
        : "https://github.com/reblocke/VBG_interpreter/blob/main/docs/EVIDENCE.md";
      const anchor = node("a", "Method source");
      anchor.href = href;
      anchor.rel = "noopener noreferrer";
      methods.append(anchor);
    }
  }
  const details = node("details");
  details.append(node("summary", "Input and output provenance"));
  for (const calc of calculations.filter((c) => c.status === "AVAILABLE")) {
    details.append(
      node(
        "p",
        `${label(calc.method_id)}: ${label(calc.output_provenance)}. Inputs: ${Object.entries(
          calc.input_origins,
        )
          .map(([key, origin]) => `${label(key)} (${label(origin)})`)
          .join(", ")}.`,
      ),
    );
  }
  const partition = result.chemistry.venous_stewart_partition;
  if (partition.status === "AVAILABLE") {
    metric(
      details,
      "Partition numerical closure error",
      partition.values.closure_error,
      "mmol/L",
    );
    metric(
      details,
      "Reconstructed venous SBE",
      partition.values.reconstructed_sbe,
      "mmol/L",
    );
  }
  if (provisional.status === "AVAILABLE") {
    const expected = node("details");
    expected.append(node("summary", "Compensation comparison used"));
    for (const [key, value] of Object.entries(
      provisional.assessment.expected_compensation,
    ))
      metric(expected, label(key), value);
    methods.append(expected);
  }
  methods.append(details);
  document.getElementById("results-panel").hidden = false;
}
