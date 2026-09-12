// Presentation precision only; classifications and arithmetic remain in Python.
export function formatNumber(value, kind = "other") {
  if (typeof value !== "number") return String(value);
  if (Math.abs(value) >= 1e5 || (value !== 0 && Math.abs(value) < 0.001))
    return value.toExponential(2);
  const places = kind === "ph" ? 2 : 1;
  return value.toLocaleString("en-US", {
    minimumFractionDigits: places,
    maximumFractionDigits: places,
  });
}
