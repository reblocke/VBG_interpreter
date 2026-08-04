const SVG_NAMESPACE = "http://www.w3.org/2000/svg";
const RESULT_SCHEMA_VERSION = "vbg_explorer_result/2.0";

const refs = {
  empty: document.querySelector("#results-empty"),
  content: document.querySelector("#results-content"),
  interpretationSummary: document.querySelector("#interpretation-summary"),
  observed: document.querySelector("#observed-result"),
  candidate: document.querySelector("#candidate-result"),
  stateSummary: document.querySelector("#state-space-summary"),
  stateFigure: document.querySelector("#state-space-figure"),
  statePlot: document.querySelector("#state-space-plot"),
  stateLegend: document.querySelector("#state-space-legend"),
  stateTableBody: document.querySelector("#state-space-table tbody"),
  features: document.querySelector("#feature-conclusions"),
  chemistry: document.querySelector("#chemistry-result"),
  history: document.querySelector("#history-result"),
  limitations: document.querySelector("#limitations-list"),
  informationNeeds: document.querySelector("#information-needs-list"),
  provenance: document.querySelector("#provenance-result"),
  generic: document.querySelector("#generic-result"),
};

function isRecord(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function humanize(value) {
  if (typeof value !== "string") {
    return String(value);
  }
  const words = value.replaceAll("_", " ");
  if (/^[A-Z0-9 ]+$/.test(words)) {
    return words
      .toLowerCase()
      .replace(/\b\w/g, (character) => character.toUpperCase());
  }
  return words.replace(/\b\w/g, (character) => character.toUpperCase());
}

function formattedScalar(value) {
  if (value === null || value === undefined) {
    return "Not provided";
  }
  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      return "Not available";
    }
    return new Intl.NumberFormat("en-US", {
      maximumFractionDigits: 4,
      useGrouping: false,
    }).format(value);
  }
  return String(value);
}

function element(tagName, text = null, className = null) {
  const node = document.createElement(tagName);
  if (text !== null) {
    node.textContent = text;
  }
  if (className) {
    node.className = className;
  }
  return node;
}

function svgElement(tagName, attributes = {}, text = null) {
  const node = document.createElementNS(SVG_NAMESPACE, tagName);
  for (const [name, value] of Object.entries(attributes)) {
    node.setAttribute(name, String(value));
  }
  if (text !== null) {
    node.textContent = text;
  }
  return node;
}

function statusBadge(status) {
  const badge = element("span", humanize(status), "status-badge");
  badge.dataset.status = typeof status === "string" ? status : "UNKNOWN";
  return badge;
}

function metricGrid(metrics) {
  const list = element("dl", null, "metric-grid");
  for (const [label, value] of metrics) {
    const wrapper = element("div", null, "metric");
    wrapper.append(element("dt", label), element("dd", formattedScalar(value)));
    list.append(wrapper);
  }
  return list;
}

function codeList(codes, emptyText) {
  const list = element("ul");
  const values = Array.isArray(codes) ? codes : [];
  if (values.length === 0) {
    list.append(element("li", emptyText, "structured-empty"));
    return list;
  }
  for (const code of values) {
    list.append(element("li", humanize(code)));
  }
  return list;
}

function renderObserved(observed, completedGas, venousOrientation) {
  refs.observed.replaceChildren();
  if (!isRecord(observed)) {
    refs.observed.append(element("p", "Observed VBG data were not returned.", "structured-empty"));
    return;
  }

  refs.observed.append(element("h4", "Measured venous inputs"));
  refs.observed.append(
    metricGrid([
      ["Measured venous pH", observed.ph],
      ["Measured PvCO₂ (input)", observed.pco2_input ?? observed.pco2],
      ["Measured PvCO₂ unit", observed.pco2_unit],
      ["PvCO₂ after unit conversion (mmHg)", observed.pco2_mmhg],
      ["Supplied blood-gas HCO₃ (mmol/L)", observed.hco3_mmol_l],
      ["HCO₃ basis", observed.hco3_basis],
      ["Venous base excess (mmol/L)", observed.base_excess_mmol_l],
      ["Specimen type", observed.specimen_type],
      ["Draw site", observed.draw_site],
    ]),
  );

  const saturation = observed.venous_o2_saturation;
  if (isRecord(saturation)) {
    refs.observed.append(
      element(
        "p",
        `Venous O₂ saturation: ${formattedScalar(saturation.value)} (${formattedScalar(
          saturation.unit,
        )}); normalized ${formattedScalar(saturation.normalized_percentage_points)} percentage points.`,
        "evidence-note",
      ),
    );
  }

  if (!isRecord(completedGas)) {
    refs.observed.append(
      element("p", "The completed venous gas was not returned.", "structured-empty"),
    );
    return;
  }

  refs.observed.append(
    element("h4", "Completed venous gas — never arterial"),
    element(
      "p",
      "This algebraic completion derives only a missing pH, PvCO₂, or blood-gas HCO₃ coordinate. Supplied values remain distinct from derived values.",
      "evidence-note",
    ),
    metricGrid([
      ["Venous pH", completedGas.ph],
      [
        "Venous pH origin",
        typeof completedGas.ph_origin === "string"
          ? humanize(completedGas.ph_origin)
          : completedGas.ph_origin,
      ],
      ["PvCO₂ (mmHg)", completedGas.pco2_mmhg],
      [
        "PvCO₂ origin",
        typeof completedGas.pco2_origin === "string"
          ? humanize(completedGas.pco2_origin)
          : completedGas.pco2_origin,
      ],
      ["Blood-gas HCO₃ (mmol/L)", completedGas.hco3_mmol_l],
      [
        "Blood-gas HCO₃ origin",
        typeof completedGas.hco3_origin === "string"
          ? humanize(completedGas.hco3_origin)
          : completedGas.hco3_origin,
      ],
      ["HCO₃ from supplied pH and PvCO₂ (mmol/L)", completedGas.hco3_ph_pco2_comparator_mmol_l],
      ["Reported-minus-comparator HCO₃ (mmol/L)", completedGas.hco3_discrepancy_mmol_l],
    ]),
  );
  if (isRecord(venousOrientation)) {
    refs.observed.append(
      element("h4", "Venous-only pH orientation"),
      metricGrid([
        [
          "pH orientation relative to ruleset reference band",
          typeof venousOrientation.ph_reference_orientation === "string"
            ? humanize(venousOrientation.ph_reference_orientation)
            : venousOrientation.ph_reference_orientation,
        ],
      ]),
      element(
        "p",
        "This descriptive venous orientation is not an arterial Boston classification.",
        "evidence-note",
      ),
    );
  }
  if (Array.isArray(completedGas.limitation_codes) && completedGas.limitation_codes.length) {
    refs.observed.append(
      element("h4", "Completed-gas limitations"),
      codeList(completedGas.limitation_codes, "None returned"),
    );
  }
}

function evidenceText(label, evidence) {
  if (!isRecord(evidence)) {
    return `${label} evidence metadata were not returned.`;
  }
  const externallyValidated = evidence.external_validation === true ? "yes" : "no";
  return `${label}: ${humanize(evidence.evidence_tier)}; external validation: ${externallyValidated}.`;
}

function renderCandidate(candidate) {
  refs.candidate.replaceChildren();
  if (!isRecord(candidate)) {
    refs.candidate.append(
      element("p", "A candidate arterial region was not returned.", "structured-empty"),
    );
    return;
  }

  refs.candidate.append(statusBadge(candidate.status));
  if (candidate.status !== "AVAILABLE") {
    refs.candidate.append(
      element("h4", "Why the model was not evaluated"),
      codeList(candidate.reason_codes, "No reason code was returned."),
    );
    return;
  }

  const point = isRecord(candidate.point) ? candidate.point : {};
  const phInterval = isRecord(candidate.ph_interval) ? candidate.ph_interval : {};
  const paco2Interval = isRecord(candidate.paco2_interval) ? candidate.paco2_interval : {};
  refs.candidate.append(
    element(
      "p",
      "Best-guess arterial orientation only: this is not a measured arterial sample or an individual correction.",
      "evidence-note",
    ),
    metricGrid([
      ["Best-guess arterial pH orientation", point.ph],
      ["Best-guess PaCO₂ orientation (mmHg)", point.paco2_mmhg],
      ["pH scenario lower", phInterval.lower],
      ["pH scenario upper", phInterval.upper],
      ["PaCO₂ scenario lower (mmHg)", paco2Interval.lower],
      ["PaCO₂ scenario upper (mmHg)", paco2Interval.upper],
      ["pH component model", candidate.ph_model_id],
      ["PaCO₂ component model", candidate.paco2_model_id],
      ["pH scenario profile", candidate.ph_profile_id],
      ["PaCO₂ scenario profile", candidate.paco2_profile_id],
    ]),
    element("p", evidenceText("Modeled pH", candidate.ph_evidence), "evidence-note"),
    element("p", evidenceText("Modeled PaCO₂", candidate.paco2_evidence), "evidence-note"),
    element(
      "p",
      "A generic component uses a published study-level agreement-extrema scenario envelope. It is not a probability, confidence, or calibrated prediction interval, and the pH and PaCO₂ axes are not jointly validated.",
      "evidence-note",
    ),
  );

  if (Array.isArray(candidate.warning_codes) && candidate.warning_codes.length) {
    refs.candidate.append(element("h4", "Model warnings"), codeList(candidate.warning_codes, "None"));
  }
  if (Array.isArray(candidate.limitation_codes) && candidate.limitation_codes.length) {
    refs.candidate.append(
      element("h4", "Model limitations"),
      codeList(candidate.limitation_codes, "None returned"),
    );
  }
}

function renderInterpretationSummary(stateSpace, candidate) {
  refs.interpretationSummary.replaceChildren();
  const status = stateSpace?.enumeration_status;
  if (status === "CERTIFIED_EXHAUSTIVE" && Array.isArray(stateSpace?.possible_signatures)) {
    const count = stateSpace.possible_signatures.length;
    refs.interpretationSummary.append(
      statusBadge(status),
      element(
        "p",
        `The certified modelled region contains ${count} feasible categorical ${count === 1 ? "state" : "states"}. The Explorer does not select an individual diagnosis from the modelled point or display samples.`,
      ),
    );
    return;
  }
  if (status === "CERTIFICATION_FAILED") {
    refs.interpretationSummary.append(
      statusBadge(status),
      element(
        "p",
        "No possible or excluded arterial state is published because the state-space proof did not complete. Observed VBG and chemistry findings remain separate.",
      ),
    );
    return;
  }
  const candidateReasons = Array.isArray(candidate?.reason_codes)
    ? candidate.reason_codes.map(humanize).join(", ")
    : "the required model context was unavailable";
  refs.interpretationSummary.append(
    statusBadge(status ?? "NOT_EVALUATED"),
    element(
      "p",
      `No candidate arterial state space was evaluated because ${candidateReasons}. Observed VBG and chemistry findings remain available without an arterial exclusion claim.`,
    ),
  );
}

function stateGroupKey(sample) {
  const signatures = Array.isArray(sample?.signatures) ? sample.signatures : [];
  return signatures.map(signatureKey).sort().join("||") || "UNCLASSIFIED";
}

function signatureKey(signature) {
  return [
    signature?.chronicity_branch,
    signature?.acid_base_state,
    signature?.primary_process,
    signature?.expected_compensation,
    signature?.measured_vs_expected,
    signature?.mixed_disorder_flag,
  ].join("|");
}

function stateGroupLabel(sample) {
  const signatures = Array.isArray(sample?.signatures) ? sample.signatures : [];
  const descriptions = signatures.map(signatureDescription);
  return descriptions.join(" / ") || "No structured state returned";
}

function signatureDescription(signature) {
  const fields = [
    ["chronicity branch", signature?.chronicity_branch],
    ["pH state", signature?.acid_base_state],
    ["primary process", signature?.primary_process],
    ["expected compensation", signature?.expected_compensation],
    ["measured versus expected", signature?.measured_vs_expected],
    ["mixed-disorder flag", signature?.mixed_disorder_flag],
  ];
  const description = fields
    .filter(([, value]) => value !== undefined)
    .map(([label, value]) =>
      `${label} ${typeof value === "string" ? humanize(value) : formattedScalar(value)}`,
    )
    .join("; ");
  return description || "No structured state returned";
}

function sampleStateDescription(sample) {
  const signatures = Array.isArray(sample?.signatures) ? sample.signatures : [];
  const descriptions = signatures.map(signatureDescription);
  return `Display-only sample at pH ${formattedScalar(sample?.ph)} and PaCO₂ ${formattedScalar(
    sample?.paco2_mmhg,
  )} mmHg. ${descriptions.join(". ") || "No structured state returned"}.`;
}

function appendSampleMarker(parent, xPosition, yPosition, markerIndex, label) {
  const markerClass = `plot-sample marker-${markerIndex % 10}`;
  const accessibleAttributes = {
    "aria-label": label,
    class: markerClass,
    role: "img",
    tabindex: 0,
  };
  const shape = markerIndex % 6;
  let marker;
  if (shape === 0) {
    marker = svgElement("circle", { ...accessibleAttributes, cx: xPosition, cy: yPosition, r: 4.7 });
  } else if (shape === 1) {
    marker = svgElement("rect", {
      ...accessibleAttributes,
      x: xPosition - 4.5,
      y: yPosition - 4.5,
      width: 9,
      height: 9,
    });
  } else if (shape === 2) {
    marker = svgElement("polygon", {
      ...accessibleAttributes,
      points: `${xPosition},${yPosition - 5.5} ${xPosition - 5},${yPosition + 4.5} ${xPosition + 5},${yPosition + 4.5}`,
    });
  } else if (shape === 3) {
    marker = svgElement("polygon", {
      ...accessibleAttributes,
      points: `${xPosition},${yPosition - 5.5} ${xPosition - 5.5},${yPosition} ${xPosition},${yPosition + 5.5} ${xPosition + 5.5},${yPosition}`,
    });
  } else if (shape === 4) {
    marker = svgElement("path", {
      ...accessibleAttributes,
      class: `${markerClass} plot-sample-line`,
      d: `M ${xPosition - 5} ${yPosition} H ${xPosition + 5} M ${xPosition} ${yPosition - 5} V ${yPosition + 5}`,
    });
  } else {
    marker = svgElement("path", {
      ...accessibleAttributes,
      class: `${markerClass} plot-sample-line`,
      d: `M ${xPosition - 4} ${yPosition - 4} L ${xPosition + 4} ${yPosition + 4} M ${xPosition + 4} ${yPosition - 4} L ${xPosition - 4} ${yPosition + 4}`,
    });
  }
  marker.append(svgElement("title", {}, label));
  parent.append(marker);
}

function drawCandidateRegion(candidate, stateSpace) {
  refs.statePlot.replaceChildren();
  refs.stateLegend.replaceChildren();
  const title = svgElement(
    "title",
    { id: "state-space-plot-title" },
    "Candidate arterial PaCO2 and pH region",
  );
  const description = svgElement(
    "desc",
    { id: "state-space-plot-description" },
    "A deterministic rectangular candidate region with a display-only categorical map and modeled point. Cell color, marker color, and marker shape distinguish sampled process sets; the table lists every certified state signature. Cell counts and area are not inference.",
  );
  refs.statePlot.append(title, description);

  const phInterval = candidate?.ph_interval;
  const paco2Interval = candidate?.paco2_interval;
  const point = candidate?.point;
  const numbers = [
    phInterval?.lower,
    phInterval?.upper,
    paco2Interval?.lower,
    paco2Interval?.upper,
    point?.ph,
    point?.paco2_mmhg,
  ];
  if (numbers.some((value) => typeof value !== "number" || !Number.isFinite(value))) {
    refs.stateFigure.hidden = true;
    return;
  }

  const plot = { left: 82, right: 690, top: 28, bottom: 318 };
  const pco2Span = Math.max(paco2Interval.upper - paco2Interval.lower, 0.1);
  const phSpan = Math.max(phInterval.upper - phInterval.lower, 0.001);
  const xMinimum = paco2Interval.lower - pco2Span * 0.12;
  const xMaximum = paco2Interval.upper + pco2Span * 0.12;
  const yMinimum = phInterval.lower - phSpan * 0.12;
  const yMaximum = phInterval.upper + phSpan * 0.12;
  const x = (value) =>
    plot.left + ((value - xMinimum) / (xMaximum - xMinimum)) * (plot.right - plot.left);
  const y = (value) =>
    plot.bottom - ((value - yMinimum) / (yMaximum - yMinimum)) * (plot.bottom - plot.top);

  for (const fraction of [0, 0.5, 1]) {
    const xPosition = plot.left + fraction * (plot.right - plot.left);
    const yPosition = plot.bottom - fraction * (plot.bottom - plot.top);
    refs.statePlot.append(
      svgElement("line", {
        x1: xPosition,
        y1: plot.top,
        x2: xPosition,
        y2: plot.bottom,
        class: "plot-grid",
      }),
      svgElement("line", {
        x1: plot.left,
        y1: yPosition,
        x2: plot.right,
        y2: yPosition,
        class: "plot-grid",
      }),
    );
  }

  const samples = Array.isArray(stateSpace?.coordinate_view?.samples)
    ? stateSpace.coordinate_view.samples
    : [];
  const groupKeys = [...new Set(samples.map(stateGroupKey))].sort();
  const groupIndexes = new Map(groupKeys.map((key, index) => [key, index]));
  const pco2Axis = [...new Set(samples.map((sample) => sample?.paco2_mmhg))]
    .filter((value) => typeof value === "number" && Number.isFinite(value))
    .sort((left, right) => left - right);
  const phAxis = [...new Set(samples.map((sample) => sample?.ph))]
    .filter((value) => typeof value === "number" && Number.isFinite(value))
    .sort((left, right) => left - right);
  const regionLeft = x(paco2Interval.lower);
  const regionTop = y(phInterval.upper);
  const regionWidth = x(paco2Interval.upper) - regionLeft;
  const regionHeight = y(phInterval.lower) - regionTop;

  refs.statePlot.append(
    svgElement("line", {
      x1: plot.left,
      y1: plot.bottom,
      x2: plot.right,
      y2: plot.bottom,
      class: "plot-axis",
    }),
    svgElement("line", {
      x1: plot.left,
      y1: plot.top,
      x2: plot.left,
      y2: plot.bottom,
      class: "plot-axis",
    }),
    svgElement("rect", {
      x: regionLeft,
      y: regionTop,
      width: regionWidth,
      height: regionHeight,
      rx: 4,
      class: "plot-region",
    }),
  );

  for (const sample of samples) {
    const pco2Index = pco2Axis.indexOf(sample?.paco2_mmhg);
    const phIndex = phAxis.indexOf(sample?.ph);
    if (pco2Index < 0 || phIndex < 0 || pco2Axis.length === 0 || phAxis.length === 0) {
      continue;
    }
    refs.statePlot.append(
      svgElement("rect", {
        x: regionLeft + (pco2Index * regionWidth) / pco2Axis.length,
        y: regionTop + ((phAxis.length - phIndex - 1) * regionHeight) / phAxis.length,
        width: regionWidth / pco2Axis.length,
        height: regionHeight / phAxis.length,
        class: `plot-display-cell marker-${(groupIndexes.get(stateGroupKey(sample)) ?? 0) % 10}`,
        "aria-hidden": "true",
      }),
    );
  }
  refs.statePlot.append(
    svgElement("rect", {
      x: regionLeft,
      y: regionTop,
      width: regionWidth,
      height: regionHeight,
      rx: 4,
      class: "plot-region-outline",
      "aria-hidden": "true",
    }),
  );

  for (const sample of samples) {
    if (
      typeof sample?.ph !== "number" ||
      !Number.isFinite(sample.ph) ||
      typeof sample?.paco2_mmhg !== "number" ||
      !Number.isFinite(sample.paco2_mmhg)
    ) {
      continue;
    }
    appendSampleMarker(
      refs.statePlot,
      x(sample.paco2_mmhg),
      y(sample.ph),
      groupIndexes.get(stateGroupKey(sample)) ?? 0,
      sampleStateDescription(sample),
    );
  }
  refs.statePlot.append(
    svgElement("circle", {
      cx: x(point.paco2_mmhg),
      cy: y(point.ph),
      r: 9,
      class: "plot-point",
    }),
  );

  for (const key of groupKeys) {
    const index = groupIndexes.get(key) ?? 0;
    const sample = samples.find((item) => stateGroupKey(item) === key);
    const item = element("li");
    const marker = element("span", ["●", "■", "▲", "◆", "+", "×"][index % 6]);
    marker.className = `legend-marker marker-${index % 10}`;
    marker.setAttribute("aria-hidden", "true");
    item.append(marker, document.createTextNode(stateGroupLabel(sample)));
    refs.stateLegend.append(item);
  }

  for (const [value, anchor] of [
    [paco2Interval.lower, "start"],
    [paco2Interval.upper, "end"],
  ]) {
    refs.statePlot.append(
      svgElement(
        "text",
        { x: x(value), y: 348, "text-anchor": anchor, class: "plot-tick" },
        formattedScalar(value),
      ),
    );
  }
  for (const value of [phInterval.lower, phInterval.upper]) {
    refs.statePlot.append(
      svgElement(
        "text",
        { x: 70, y: y(value) + 6, "text-anchor": "end", class: "plot-tick" },
        formattedScalar(value),
      ),
    );
  }
  refs.statePlot.append(
    svgElement(
      "text",
      { x: (plot.left + plot.right) / 2, y: 382, "text-anchor": "middle", class: "plot-label" },
      "Candidate arterial PaCO₂ (mmHg)",
    ),
    svgElement(
      "text",
      {
        x: 22,
        y: (plot.top + plot.bottom) / 2,
        transform: `rotate(-90 22 ${(plot.top + plot.bottom) / 2})`,
        "text-anchor": "middle",
        class: "plot-label",
      },
      "Candidate arterial pH",
    ),
  );
  refs.stateFigure.hidden = false;
}

function renderFeatureConclusionBuckets(conclusions) {
  refs.features.replaceChildren();
  const groups = [
    [
      "PRESENT_ACROSS_ALL_MODELED_STATES",
      "Present across all modeled states",
      "Each listed feature occurs in every feasible state of this modeled region.",
    ],
    [
      "POSSIBLE_IN_SOME_MODELED_STATES",
      "Possible in some modeled states",
      "Each listed feature occurs in at least one, but not every, feasible state.",
    ],
    [
      "EXCLUDED_WITHIN_MODELED_STATE_SPACE",
      "Excluded within the modeled state space",
      "These features are excluded only within this modeled state space; they are not globally excluded for a person.",
    ],
    [
      "NOT_EVALUABLE",
      "Not evaluable with the supplied information",
      "No modeled-state conclusion is available for these features.",
    ],
  ];
  for (const [status, heading, explanation] of groups) {
    const matches = conclusions.filter((conclusion) => conclusion?.status === status);
    if (matches.length === 0) {
      continue;
    }
    const section = element("section", null, "feature-conclusion-group");
    const list = element("ul", null, "feature-list");
    for (const conclusion of matches) {
      list.append(element("li", humanize(conclusion.feature_id)));
    }
    section.append(element("h4", heading), element("p", explanation, "evidence-note"), list);
    refs.features.append(section);
  }
}

function renderStateSpace(stateSpace, candidate) {
  refs.stateSummary.textContent = "";
  refs.stateTableBody.replaceChildren();
  refs.stateLegend.replaceChildren();
  refs.stateFigure.hidden = true;

  if (!isRecord(stateSpace)) {
    refs.stateSummary.textContent = "State-space information was not returned.";
    appendEmptyStateRow();
    return;
  }

  const status = stateSpace.enumeration_status ?? "NOT_EVALUATED";
  refs.stateSummary.replaceChildren(statusBadge(status));
  const signatures = Array.isArray(stateSpace.possible_signatures)
    ? stateSpace.possible_signatures
    : [];

  if (status === "CERTIFIED_EXHAUSTIVE" && signatures.length > 0) {
    refs.stateSummary.append(
      document.createTextNode(
        ` ${signatures.length} distinct categorical ${signatures.length === 1 ? "state was" : "states were"} discovered. Counts do not represent likelihood or frequency.`,
      ),
    );
    const method = stateSpace.coverage_method_id
      ? ` Coverage method: ${formattedScalar(stateSpace.coverage_method_id)}.`
      : "";
    const resolution = stateSpace.coordinate_view?.display_grid_resolution;
    const displayNote = Number.isInteger(resolution)
      ? ` The coordinate visual uses a ${resolution} by ${resolution} display-only grid; enumeration does not depend on that grid.`
      : "";
    refs.stateSummary.append(document.createTextNode(`${method}${displayNote}`));
    drawCandidateRegion(candidate, stateSpace);
    for (const signature of signatures) {
      const row = element("tr");
      for (const value of [
        signature?.chronicity_branch,
        signature?.acid_base_state,
        signature?.primary_process,
        signature?.expected_compensation,
        signature?.measured_vs_expected,
        signature?.mixed_disorder_flag,
      ]) {
        row.append(
          element("td", typeof value === "string" ? humanize(value) : formattedScalar(value)),
        );
      }
      refs.stateTableBody.append(row);
    }
  } else {
    refs.stateSummary.append(
      document.createTextNode(
        " No scientific state-space conclusions are published unless enumeration is certified exhaustive.",
      ),
    );
    appendEmptyStateRow();
  }

  const conclusions = Array.isArray(stateSpace.feature_conclusions)
    ? stateSpace.feature_conclusions
    : [];
  renderFeatureConclusionBuckets(conclusions);
}

function appendEmptyStateRow() {
  const row = element("tr");
  const cell = element("td", "No certified categorical states were published.", "structured-empty");
  cell.colSpan = 6;
  row.append(cell);
  refs.stateTableBody.append(row);
}

function renderChemistry(chemistry) {
  refs.chemistry.replaceChildren();
  if (!isRecord(chemistry)) {
    refs.chemistry.append(element("p", "Chemistry interpretation was not returned.", "structured-empty"));
    return;
  }
  refs.chemistry.append(
    statusBadge(chemistry.status),
    metricGrid([
      [
        "Chemistry relationship to current VBG",
        typeof chemistry.relationship_to_vbg === "string"
          ? humanize(chemistry.relationship_to_vbg)
          : chemistry.relationship_to_vbg,
      ],
      ["Sodium (mmol/L)", chemistry.sodium_mmol_l],
      ["Chloride (mmol/L)", chemistry.chloride_mmol_l],
      ["Serum total CO₂ (mmol/L)", chemistry.serum_total_co2_mmol_l],
      ["Albumin (g/L)", chemistry.albumin_g_l],
      ["Lactate (mmol/L)", chemistry.lactate_mmol_l],
      ["Anion gap (mmol/L)", chemistry.anion_gap_mmol_l],
      ["Albumin-corrected anion gap (mmol/L)", chemistry.corrected_anion_gap_mmol_l],
    ]),
  );
  if (Array.isArray(chemistry.limitation_codes) && chemistry.limitation_codes.length) {
    refs.chemistry.append(
      element("h4", "Chemistry limitations"),
      codeList(chemistry.limitation_codes, "None returned"),
    );
  }
  if (isRecord(chemistry.stewart_partition)) {
    refs.chemistry.append(
      element("h4", "Venous-basis Stewart partition"),
      statusBadge(chemistry.stewart_partition.status),
      renderStructuredValue(chemistry.stewart_partition, 0),
    );
  }
  if (Array.isArray(chemistry.identifiable_components)) {
    refs.chemistry.append(
      element("h4", "Identifiable chemistry components"),
      codeList(chemistry.identifiable_components, "No additional component was identifiable."),
    );
  }
  if (Array.isArray(chemistry.nonidentifiable_components)) {
    refs.chemistry.append(
      element("h4", "Nonidentifiable chemistry components"),
      codeList(chemistry.nonidentifiable_components, "No additional limitation returned."),
    );
  }
}

function renderHistory(history) {
  refs.history.replaceChildren();
  if (!isRecord(history)) {
    refs.history.append(element("p", "Longitudinal context was not returned.", "structured-empty"));
    return;
  }
  refs.history.append(statusBadge(history.status));
  if (isRecord(history.prior_observation)) {
    refs.history.append(renderStructuredValue(history.prior_observation, 0));
  } else {
    refs.history.append(element("p", "No prior observation was provided.", "structured-empty"));
  }
  if (Array.isArray(history.limitation_codes) && history.limitation_codes.length) {
    refs.history.append(
      element("h4", "Longitudinal limitations"),
      codeList(history.limitation_codes, "None returned"),
    );
  }
}

function renderCodeListInto(target, codes, emptyText) {
  const list = codeList(codes, emptyText);
  target.replaceChildren(...list.children);
}

function renderStructuredValue(value, depth) {
  if (depth > 8) {
    return element("p", "Nested data omitted at the display depth limit.", "structured-empty");
  }
  if (Array.isArray(value)) {
    if (value.length === 0) {
      return element("p", "None", "structured-empty");
    }
    const list = element("ol", null, "structured-array");
    for (const item of value) {
      const listItem = element("li");
      listItem.append(renderStructuredValue(item, depth + 1));
      list.append(listItem);
    }
    return list;
  }
  if (isRecord(value)) {
    const list = element("dl", null, "structured-object");
    const entries = Object.entries(value);
    if (entries.length === 0) {
      return element("p", "None", "structured-empty");
    }
    for (const [key, nestedValue] of entries) {
      const wrapper = element("div", null, "structured-field");
      const term = element("dt", humanize(key));
      const definition = element("dd");
      if (isRecord(nestedValue) || Array.isArray(nestedValue)) {
        definition.append(renderStructuredValue(nestedValue, depth + 1));
      } else {
        definition.textContent = formattedScalar(nestedValue);
      }
      wrapper.append(term, definition);
      list.append(wrapper);
    }
    return list;
  }
  return element("span", formattedScalar(value));
}

function resultObject(payload) {
  if (!isRecord(payload) || Object.keys(payload).length !== 1 || !isRecord(payload.result)) {
    return null;
  }
  const result = payload.result;
  // Python owns the detailed result contract. This small transport guard only
  // prevents a malformed worker response from being rendered as an Explorer
  // result; it deliberately does not duplicate the Python output schema.
  if (
    result.schema_version !== RESULT_SCHEMA_VERSION ||
    !isRecord(result.observed_vbg) ||
    !isRecord(result.completed_venous_gas) ||
    !isRecord(result.venous_orientation) ||
    !isRecord(result.candidate_arterial_region) ||
    !isRecord(result.state_space) ||
    !isRecord(result.chemistry) ||
    !isRecord(result.longitudinal_context) ||
    !Array.isArray(result.limitations) ||
    !Array.isArray(result.information_that_would_reduce_ambiguity) ||
    !isRecord(result.provenance)
  ) {
    return null;
  }
  return result;
}

export function clearExplorerResult() {
  refs.empty.hidden = false;
  refs.content.hidden = true;
  refs.interpretationSummary.replaceChildren();
  refs.observed.replaceChildren();
  refs.candidate.replaceChildren();
  refs.stateSummary.textContent = "";
  refs.stateFigure.hidden = true;
  refs.statePlot.replaceChildren();
  refs.stateLegend.replaceChildren();
  refs.stateTableBody.replaceChildren();
  refs.features.replaceChildren();
  refs.chemistry.replaceChildren();
  refs.history.replaceChildren();
  refs.limitations.replaceChildren();
  refs.informationNeeds.replaceChildren();
  refs.provenance.replaceChildren();
  refs.generic.replaceChildren();
}

export function renderExplorerResult(payload) {
  const result = resultObject(payload);
  if (!result) {
    throw new Error("The interpretation engine returned an invalid result object.");
  }

  renderInterpretationSummary(result.state_space, result.candidate_arterial_region);
  renderObserved(
    result.observed_vbg ?? result.normalized_input?.current_vbg,
    result.completed_venous_gas,
    result.venous_orientation,
  );
  renderCandidate(result.candidate_arterial_region);
  renderStateSpace(result.state_space, result.candidate_arterial_region);
  renderChemistry(result.chemistry);
  renderHistory(result.longitudinal_context);
  renderCodeListInto(refs.limitations, result.limitations, "No additional limitations returned.");
  renderCodeListInto(
    refs.informationNeeds,
    result.information_that_would_reduce_ambiguity,
    "No additional information need returned.",
  );
  refs.provenance.replaceChildren(
    isRecord(result.provenance)
      ? renderStructuredValue(result.provenance, 0)
      : element("p", "Provenance was not returned.", "structured-empty"),
  );
  refs.generic.replaceChildren(renderStructuredValue(result, 0));

  refs.empty.hidden = true;
  refs.content.hidden = false;
}
