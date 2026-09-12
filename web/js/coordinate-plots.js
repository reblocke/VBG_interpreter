import { formatNumber } from "./format.js";
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
const number = formatNumber;
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
  const direction = result.physiology_direction;
  const axes = direction.axes;
  const pH = result.arterial_ph_estimate,
    co2 = result.arterial_paco2_estimate;
  const phBound = axes.ph.status === "AVAILABLE" ? axes.ph.bound : null;
  const co2Bound = axes.pco2.status === "AVAILABLE" ? axes.pco2.bound : null;
  const known =
    phBound !== null && co2Bound !== null
      ? { ph: phBound, co2: co2Bound }
      : null;
  // Warned arithmetic stays in the detail cards and cannot stretch the physiology viewport.
  const estimated =
    phBound !== null &&
    co2Bound !== null &&
    pH.status === "AVAILABLE" &&
    co2.status === "AVAILABLE"
      ? {
          ph: pH.values.ph,
          co2: co2.values.point,
          lower: co2.values.lower,
          upper: co2.values.upper,
        }
      : null;
  const xRange = paddedRange([phBound, estimated?.ph], 7, 7.8);
  const yRange = paddedRange(
    [co2Bound, estimated?.co2, estimated?.lower, estimated?.upper],
    20,
    80,
  );
  yRange[0] = Math.max(0, yRange[0]);
  draw(
    "known-plot",
    "Measured venous coordinates",
    known,
    xRange,
    yRange,
    "measured",
    direction,
  );
  draw(
    "estimated-plot",
    "Estimated arterial coordinates",
    estimated,
    xRange,
    yRange,
    "estimated",
    null,
  );
}
function draw(id, title, point, xr, yr, kind, direction) {
  const parent = document.getElementById(id);
  parent.replaceChildren();
  const partial =
    direction &&
    Object.values(direction.axes).some((a) => a.status === "AVAILABLE");
  if (!point && !partial) {
    parent.append(
      html(
        "p",
        kind === "measured"
          ? "No usable measured coordinate is available for a physiology display. Available values remain below."
          : "Coordinate display requires both available arterial estimates. Available estimates remain below.",
      ),
    );
    return;
  }
  const description = point
    ? `${title}: pH ${number(point.ph, "ph")}, CO₂ ${number(point.co2)} mmHg.`
    : "Partial measured coordinates; no paired point is inferred.";
  const figure = document.createElement("figure");
  figure.className = `coordinate-figure ${kind}`;
  const caption = html("figcaption", description);
  caption.id = `${id}-caption`;
  const svg = svgNode("svg", {
    viewBox: "0 0 400 350",
    role: "img",
    "aria-labelledby": `${id}-caption`,
    "aria-describedby": direction
      ? `${id}-description ${id}-model-description`
      : `${id}-description`,
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
  if (direction) {
    const ph = direction.axes.ph.bound,
      co2 = direction.axes.pco2.bound;
    const left = ph === null ? 65 : x(ph),
      top = co2 === null ? 40 : y(co2);
    const defs = svgNode("defs", {});
    const pattern = svgNode("pattern", {
      id: `${id}-hatch`,
      width: 14,
      height: 14,
      patternUnits: "userSpaceOnUse",
    });
    pattern.append(
      svgNode("path", {
        d: "M-3,3 L3,-3 M0,14 L14,0 M11,17 L17,11",
        class: "direction-hatch",
      }),
    );
    defs.append(pattern);
    svg.append(defs);
    const bounds = { x: left, y: top, width: 370 - left, height: 290 - top };
    svg.append(
      svgNode("rect", { ...bounds, class: "direction-fill" }),
      svgNode("rect", {
        ...bounds,
        fill: `url(#${id}-hatch)`,
        class: "direction-region",
      }),
    );
    if (ph !== null)
      svg.append(
        svgNode("line", {
          x1: left,
          x2: left,
          y1: 40,
          y2: 290,
          class: "direction-guide",
        }),
      );
    if (co2 !== null)
      svg.append(
        svgNode("line", {
          x1: 65,
          x2: 370,
          y1: top,
          y2: top,
          class: "direction-guide",
        }),
      );
    // Open arrowheads express continuation, not a new numerical bound.
    if (ph !== null) {
      const middleY = (top + 290) / 2;
      svg.append(
        svgNode("path", {
          d: `M356,${middleY} H379 M373,${middleY - 5} L379,${middleY} L373,${middleY + 5}`,
          class: "direction-arrow",
          "data-direction": "higher-ph",
        }),
      );
    }
    if (co2 !== null && yr[0] > 0) {
      const middleX = (left + 370) / 2;
      svg.append(
        svgNode("path", {
          d: `M${middleX},276 V299 M${middleX - 5},293 L${middleX},299 L${middleX + 5},293`,
          class: "direction-arrow",
          "data-direction": "lower-co2",
        }),
      );
    }
  }
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
        number(v, "ph"),
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
  if (point && Number.isFinite(point.lower) && Number.isFinite(point.upper)) {
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
  if (point) {
    svg.append(
      svgNode(
        kind === "measured" ? "circle" : "rect",
        kind === "measured"
          ? {
              cx: x(point.ph),
              cy: y(point.co2),
              r: 6,
              class: "coordinate-point",
            }
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
        `${number(point.ph, "ph")}, ${number(point.co2)}`,
      ),
    );
  }
  const detail = html(
    "p",
    "Reference cross: pH 7.40 / CO₂ 40 mmHg. Left/right: lower/higher pH; below/above: lower/higher CO₂. These shared coordinates are not validated venous cutoffs or diagnostic quadrants.",
  );
  detail.id = `${id}-description`;
  detail.className = "limitation";
  figure.append(caption, svg, detail);
  if (direction) {
    const modelText = html(
      "p",
      direction.assumption +
        " " +
        direction.summary +
        " " +
        direction.limitations.join(" "),
    );
    modelText.id = `${id}-model-description`;
    modelText.className = "visually-hidden";
    figure.append(modelText);
    figure.append(
      html("p", direction.caption),
      html("p", direction.summary),
      html(
        "p",
        "Light hatching shows the conditional direction; short-dashed guides include equality. Unshaded space is not clinically ruled out.",
      ),
    );
  }
  if (point && Number.isFinite(point.lower))
    figure.append(
      html(
        "p",
        `Vertical whisker: Farkas agreement range ${number(point.lower)}–${number(point.upper)} mmHg. CO₂ agreement only; pH uncertainty is not quantified.`,
      ),
    );
  parent.append(figure);
}
