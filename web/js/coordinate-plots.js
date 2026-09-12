// Display-only coordinates. Calculations and inference remain in Python.
const NS = "http://www.w3.org/2000/svg";
function svgNode(tag, attrs, text) {
  const el = document.createElementNS(NS, tag);
  for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
  if (text !== undefined) el.textContent = text;
  return el;
}
function html(tag, text) {
  const el = document.createElement(tag);
  el.textContent = text;
  return el;
}
function number(value) {
  return Math.abs(value) >= 1e5 || (value !== 0 && Math.abs(value) < 0.001)
    ? value.toExponential(2)
    : value.toLocaleString("en-US", { maximumFractionDigits: 3 });
}
function paddedRange(values, low, high) {
  const finite = values.filter(Number.isFinite);
  const min = Math.min(low, ...finite),
    max = Math.max(high, ...finite);
  // Scale first to avoid overflow for finite extreme source values.
  const pad = max * 0.08 - min * 0.08;
  return [
    min < low ? min - pad : low,
    max > high ? Math.min(Number.MAX_VALUE, max + pad) : high,
  ];
}
function fraction(value, [low, high]) {
  const scale = Math.max(Math.abs(low), Math.abs(high), 1);
  return (value / scale - low / scale) / (high / scale - low / scale);
}
function midpoint([low, high]) {
  return low / 2 + high / 2;
}

export function renderCoordinatePlots(result) {
  const measured = result.venous_gas.measured_values;
  const pH = result.arterial_ph_estimate,
    co2 = result.arterial_paco2_estimate;
  // Venous display entries are normalized by Python; never reconstruct a source axis here.
  const known =
    Number.isFinite(measured.ph?.value) &&
    Number.isFinite(measured.pco2?.normalized_mmhg)
      ? { ph: measured.ph.value, co2: measured.pco2.normalized_mmhg }
      : null;
  const estimated =
    pH.status === "AVAILABLE" && co2.status === "AVAILABLE"
      ? {
          ph: pH.values.ph,
          co2: co2.values.point,
          lower: co2.values.lower,
          upper: co2.values.upper,
        }
      : null;
  const xRange = paddedRange([known?.ph, estimated?.ph], 7, 7.8);
  const yRange = paddedRange(
    [known?.co2, estimated?.co2, estimated?.lower, estimated?.upper],
    20,
    80,
  );
  draw(
    "known-plot",
    "Measured venous coordinates",
    known,
    xRange,
    yRange,
    "measured",
  );
  draw(
    "estimated-plot",
    "Estimated arterial coordinates",
    estimated,
    xRange,
    yRange,
    "estimated",
  );
}
function draw(id, title, point, xr, yr, kind) {
  const parent = document.getElementById(id);
  parent.replaceChildren();
  if (!point) {
    parent.append(
      html(
        "p",
        kind === "measured"
          ? "Coordinate display requires both measured venous pH and PvCO₂. Available values remain below."
          : "Coordinate display requires both available arterial estimates. Available estimates remain below.",
      ),
    );
    return;
  }
  const description = `${title}: pH ${number(point.ph)}, CO₂ ${number(point.co2)} mmHg.`;
  const figure = document.createElement("figure");
  figure.className = `coordinate-figure ${kind}`;
  const caption = html("figcaption", description);
  caption.id = `${id}-caption`;
  const svg = svgNode("svg", {
    viewBox: "0 0 400 350",
    role: "img",
    "aria-labelledby": `${id}-caption`,
    "aria-describedby": `${id}-description`,
    "data-x-min": xr[0],
    "data-x-max": xr[1],
    "data-y-min": yr[0],
    "data-y-max": yr[1],
  });
  const x = (v) => 65 + fraction(v, xr) * 305,
    y = (v) => 290 - fraction(v, yr) * 250;
  svg.append(
    svgNode("rect", {
      x: 65,
      y: 40,
      width: 305,
      height: 250,
      class: "plot-frame",
    }),
  );
  svg.append(
    svgNode("line", {
      x1: x(7.4),
      x2: x(7.4),
      y1: 40,
      y2: 290,
      class: "reference-line",
    }),
    svgNode("line", {
      x1: 65,
      x2: 370,
      y1: y(40),
      y2: y(40),
      class: "reference-line",
    }),
  );
  for (const v of [xr[0], midpoint(xr), xr[1]]) {
    svg.append(
      svgNode(
        "text",
        { x: x(v), y: 312, "text-anchor": "middle", class: "plot-tick" },
        number(v),
      ),
    );
  }
  for (const v of [yr[0], midpoint(yr), yr[1]]) {
    svg.append(
      svgNode(
        "text",
        { x: 57, y: y(v) + 5, "text-anchor": "end", class: "plot-tick" },
        number(v),
      ),
    );
  }
  svg.append(
    svgNode(
      "text",
      { x: 218, y: 340, "text-anchor": "middle", class: "plot-axis" },
      "pH",
    ),
    svgNode("text", { x: 65, y: 22, class: "plot-axis" }, "CO₂ (mmHg)"),
  );
  if (Number.isFinite(point.lower) && Number.isFinite(point.upper)) {
    svg.append(
      svgNode("line", {
        x1: x(point.ph),
        x2: x(point.ph),
        y1: y(point.lower),
        y2: y(point.upper),
        class: "agreement-whisker",
      }),
    );
    for (const v of [point.lower, point.upper])
      svg.append(
        svgNode("line", {
          x1: x(point.ph) - 6,
          x2: x(point.ph) + 6,
          y1: y(v),
          y2: y(v),
          class: "agreement-whisker",
        }),
      );
  }
  svg.append(
    svgNode(
      kind === "measured" ? "circle" : "rect",
      kind === "measured"
        ? { cx: x(point.ph), cy: y(point.co2), r: 6, class: "coordinate-point" }
        : {
            x: x(point.ph) - 6,
            y: y(point.co2) - 6,
            width: 12,
            height: 12,
            class: "coordinate-point",
          },
    ),
  );
  // Full point coordinates remain in the wrapping caption at all widths and text sizes.
  const right = fraction(point.ph, xr) > 0.5;
  svg.append(
    svgNode(
      "text",
      {
        x: x(point.ph) + (right ? -11 : 11),
        y: y(point.co2) - 12,
        "text-anchor": right ? "end" : "start",
        class: "point-label",
      },
      `${number(point.ph)}, ${number(point.co2)}`,
    ),
  );
  const detail = html(
    "p",
    "Reference cross: pH 7.40 / CO₂ 40 mmHg. Left/right: lower/higher pH; below/above: lower/higher CO₂. These shared coordinates are not validated venous cutoffs or diagnostic quadrants.",
  );
  detail.id = `${id}-description`;
  detail.className = "limitation";
  figure.append(caption, svg, detail);
  if (Number.isFinite(point.lower))
    figure.append(
      html(
        "p",
        `Vertical whisker: Farkas agreement range ${number(point.lower)}–${number(point.upper)} mmHg; no pH or joint uncertainty region.`,
      ),
    );
  parent.append(figure);
}
