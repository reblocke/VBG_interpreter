import { renderCoordinatePlots } from "./coordinate-plots.js";
import { formatNumber } from "./format.js";
const SCHEMA = "vbg_explorer_result/6.1";
const LABELS = {
  ph: "Venous pH",
  gas_basis: "Gas bicarbonate basis",
  timing: "Chemistry timing",
  HH_FROM_MEASURED_PH_PVCO2: "HH from measured venous pH and PvCO₂",
  SUPPLIED_BLOOD_GAS_HCO3: "Supplied Blood gas HCO₃",
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
  source_pvco2: "Source venous CO₂",
  saturation_percent: "Measured venous saturation",
  STANDARD: "standard",
  ACTUAL: "actual / whole-blood",
  UNKNOWN: "unknown",
  SUPPLIED_INPUT: "supplied coordinate",
  CHAINED_UNVALIDATED: "chained / unvalidated",
  HH_RECONSTRUCTED: "HH-reconstructed",
  PERIPHERAL_CATEGORY_MATCH: "peripheral sample category; other applicability unassessed",
  PERIPHERAL_ASSUMPTION: "peripheral assumption, sample unknown",
  CENTRAL_HEURISTIC: "central sample, fixed heuristic",
  NO_EVALUATED_INTERVAL: "no evaluated interval for this heuristic",
  RECONSTRUCTED_PVCO2_CHAIN: "uncertainty not quantified for reconstructed PvCO₂",
  POINT_UNAVAILABLE: "point estimate unavailable",
  NONPHYSICAL_ENDPOINT: "nonphysical agreement endpoint",
  NOT_QUANTIFIED: "not quantified",
  UNAVAILABLE: "unavailable",
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
function renderWarnings(parent, calculation) {
  if (!calculation.input_warnings.length) return;
  const sources = calculation.input_warnings.map((warning) =>
    `${warning.origin === "HH_RECONSTRUCTED" ? "HH-reconstructed" : "supplied"} ${label(warning.field)}`,
  );
  parent.append(node("p", `Sanity warning: ${sources.join("; ")}. Finite arithmetic retained; check source values and units.`, "warning"));
}
function renderCalculation(
  parent,
  title,
  calculation,
  { showTitle = true } = {},
) {
  if (showTitle) parent.append(node("h3", title));
  renderWarnings(parent, calculation);
  if (calculation.route_label)
    parent.append(node("p", calculation.route_label, "route-label"));
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
      showTitle && visibleKeys.length === 1 ? null
        : key === "bmp_minus_gas_hco3"
          ? (calculation.values.gas_basis === "HH_FROM_MEASURED_PH_PVCO2"
            ? "BMP minus HH-calculated Blood gas HCO₃" : "BMP minus reported Blood gas HCO₃")
          : label(key),
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
        calculation.input_origins.sbe === "CALCULATED_VAN_SLYKE"
          ? "These components reconstruct calculated venous SBE (37°C assumed); the residual is not a specific diagnosis."
          : "These components reconstruct reported venous SBE; the residual is not a specific diagnosis.",
      ),
    );
  }
  if (calculation.output_provenance === "CALCULATED_VAN_SLYKE")
    parent.append(node("p", "Calculated venous SBE; 37°C assumed.", "limitation"));
  // Keep case warnings adjacent; full formula/application qualifications live in details.
  for (const limitation of calculation.limitations.filter((text) => text.startsWith("Large BMP")))
    parent.append(node("p", limitation, "warning"));
}
function optionalCalculation(parent, additional, title, calculation) {
  const numericMissing = calculation.missing_inputs.some((key) => key !== "same clinical timepoint confirmation");
  renderCalculation(numericMissing ? additional : parent, title, calculation);
}
function additionalCalculations(parent) {
  const details = node("details", undefined, "additional-calculations");
  details.append(node("summary", "Additional calculations"));
  parent.append(details);
  return details;
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
  const summaryDetails = node("details");
  summaryDetails.append(node("summary", "Interpretation details"));
  for (const text of result.narrative.details)
    summaryDetails.append(node("p", text, "limitation"));
  narrative.append(summaryDetails);
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
  const gasAdditional = additionalCalculations(gas);
  for (const [key, calc] of Object.entries(result.venous_gas.calculated_values))
    optionalCalculation(gas, gasAdditional, label(key), calc);
  if (result.venous_gas.consistency.status === "AVAILABLE")
    renderCalculation(gas, "Numerical HCO₃ consistency", result.venous_gas.consistency);
  optionalCalculation(gas, gasAdditional, "Venous standard base excess", result.venous_gas.standard_base_excess);
  gas.append(gasAdditional);
  gasAdditional.hidden = gasAdditional.children.length === 1;
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
  if (anyChemistry) {
    const additional = additionalCalculations(chemistry);
    for (const [key, calc] of Object.entries(result.chemistry))
      optionalCalculation(chemistry, additional, label(key), calc);
    chemistry.append(additional);
    additional.hidden = additional.children.length === 1;
  }
  const arterial = document.getElementById("arterial-content");
  const estimate = result.arterial_paco2_estimate;
  const ph = result.arterial_ph_estimate;
  renderCalculation(arterial, "Estimated arterial pH", ph);
  arterial.append(node("h3", "Estimated PaCO₂"));
  arterial.append(node("p", estimate.route_label, "route-label"));
  renderWarnings(arterial, estimate);
  if (estimate.agreement.status !== "AVAILABLE")
    arterial.append(node("p", `Agreement: ${label(estimate.agreement.status)} (${label(estimate.agreement.reason_code)}).`, "limitation"));
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
    if (estimate.agreement.status === "AVAILABLE")
      metric(
        arterial,
        "Peripheral-study CO₂ agreement range",
        `${number(estimate.agreement.lower)}–${number(estimate.agreement.upper)}`,
        "mmHg",
      );
    for (const text of estimate.limitations.filter((t) => /^(Agreement interval is nonphysical|Saturation exceeds)/.test(t)))
      arterial.append(node("p", text, "limitation"));
  } else {
    renderCalculation(arterial, "Estimated PaCO₂", estimate, { showTitle: false });
    arterial.append(node("p", `Selected method: ${estimate.method_id === "farkas_simplified_93_v1" ? "Farkas" : "fixed −5 mmHg correction"}; no estimate is available.`));

  }
  renderCalculation(
    arterial,
    "Modeled arterial bicarbonate",
    result.modeled_arterial_hco3,
  );
  const provisional = result.provisional_interpretation;
  const interpretationDetails = node("details");
  interpretationDetails.append(node("summary", "Provisional gas-only interpretation details"));
  arterial.append(interpretationDetails);
  if (provisional.status === "AVAILABLE") {
    interpretationDetails.append(node("p", provisional.assessment.modeled_vs_expected));
    for (const text of provisional.assessment.notes)
      interpretationDetails.append(node("p", text, "limitation"));
  } else {
    arterial.append(node("p", provisional.status === "UNAVAILABLE_UNRELIABLE_INPUT"
      ? "Interpretation withheld because a required source or HH-reconstructed coordinate has a sanity warning. Finite arithmetic is retained above."
      : `Provisional interpretation unavailable: ${label(provisional.status)}.`, "limitation"));
  }
  for (const text of provisional.limitations)
    interpretationDetails.append(node("p", text, "limitation"));
  const sensitivity = result.interpretation_sensitivity;
  interpretationDetails.append(node("h3", "CO₂ scenario sensitivity"), node("p", sensitivity.summary));
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
    interpretationDetails.append(details);
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
    for (const text of new Set(calculations.filter((c) => c.method_id === id).flatMap((c) => c.limitations)))
      methods.append(node("p", text, "limitation"));
    for (const calc of [ph, estimate].filter((c) => c.method_id === id)) {
      const choice = calc.selection;
      methods.append(node("p", `Case: ${label(choice.case_evidence)}; source: ${label(choice.source_coordinate_origin)}; ${label(choice.model_scope)}.`));

    }
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
