# Interpretation specification

## Request 5.0

`interpret_vbg(VbgExplorerRequest(...))` is the single Python entry point. Typed inputs live in
`vbg_interpreter.models`; `request_from_mapping` and `request_from_json` accept the strict wire
contract. Root keys are exactly `schema_version`, `current_vbg`, and `current_chemistry`.
All declared wire fields are present; absent measurements are null. Numeric wire inputs are
finite decimal strings, never JSON numbers or guessed units. Extra/duplicate fields and obsolete
versions are rejected without migration.

At least one current VBG value is required, including BE or saturation; chemistry alone cannot
submit. Gas pH, PCO2 and HCO3 must be positive; BE may be signed. Saturation has explicit percent
or fraction units and is declared to be from the same sample by its field definition. SpO2 and
PO2 are not substitutes. HCO3 basis is reported/calculated/unknown; BE basis is standard/actual/
unknown. Sample type is PERIPHERAL/CENTRAL/UNKNOWN (default UNKNOWN). No adverse-context, supplemental-oxygen or separate same-sample questionnaire is present. Albumin is `{value, unit}` with g/L or g/dL; normalized_g_l is output-only. Applicability is not assessed. Chemistry timing remains explicit.

## Result 5.0

The root contains schema/software versions, input summary, venous gas, chemistry, screening,
`arterial_ph_estimate`, `arterial_paco2_estimate`, `modeled_arterial_hco3`,
`provisional_interpretation`, unresolved questions, at most three next inputs, methods, `input_observations`, `physiology_direction`, `interpretation_sensitivity`, and `narrative`.
Venous gas retains measured values in original units, calculated coordinates, numerical
consistency, measured-pH reference position, and venous SBE. A supplied PCO2 entry additionally
has `normalized_mmhg` when normalization succeeds, for the measured coordinate display.

Each calculation carries status, values, units, input origins, output provenance, method ID,
evidence tier, limitations, missing inputs, and optional applicability. Statuses are AVAILABLE,
UNAVAILABLE_MISSING_INPUT, UNAVAILABLE_OUTSIDE_SCOPE, UNAVAILABLE_UNRELIABLE_INPUT, or MODEL_DOMAIN_REFUSAL. Unavailable
calculations have no numeric values. Screening remains NOT_CONFIGURED.

The provisional interpretation carries its own status, assessment, missing inputs, limitations,
method ID and provenance. Its assessment is the pinned Boston helper's structured result with
`modeled_vs_expected` replacing `measured_vs_expected`, and wording adapted for estimated inputs.
No chemistry/SBE operands are fabricated to call that gas-only helper. Chronic emphasis is disabled;
this does not establish an acute process. The helper's broad acute/chronic comparisons remain.

## Estimate selection and independent outputs

- Measured venous pH alone supports estimated arterial pH = pH + 0.04.
- Measured PvCO2 alone supports estimated PaCO2 = PvCO2(mmHg) − 5.
- Adding same-sample venous saturation to an explicitly PERIPHERAL sample selects Farkas: PvCO2 − 0.22 × (93 − saturation%).
  It replaces only the CO2 correction. No second subtraction and no saturation-based pH change.
- Fixed corrections have no uncertainty interval. Farkas retains the conservative published
  error bounds −8.74 to +9.20 mmHg, reversed into [estimate − 9.20, estimate + 8.74].
  These are population agreement bounds, not individual confidence or a joint arterial region.
- All estimates have APPLICABILITY_UNASSESSED. No removed flag is silently set to favorable.
- Both estimated coordinates enable HH-modeled arterial bicarbonate and a provisional Boston
  assessment. These depend only on source-measured pH/PvCO2 and optional saturation. Reported or
  HH-derived venous HCO3 and serum total CO2 are never substituted into this modeled gas.
- Nonpositive/nonfinite estimates, Farkas endpoints or modeled bicarbonate cause local numerical
  refusal. There is no clamping or fallback after a failing selected method. Supplied invalid
  saturation is an input error, not an instruction to use the fixed method.
- Venous HH completion, SBE and chemistry remain independent. Standard reported BE takes
  precedence; otherwise a sufficient venous pair supports calculated SBE at assumed 37°C.
  BE never gates arterial estimates or their provisional interpretation. The venous Stewart
  partition still requires measured pH, reported/calculated SBE and same-time Na/Cl/albumin.

## Displays and additional information

“What’s known” contains measurements and separately identified calculations. Its pH × CO2 plot
uses usable measured venous axes, with pressure normalized by Python. A single usable axis shows a half-plane without a point; two axes show lower-right directional shading. “Best guess” shows
estimated arterial coordinates, modeled bicarbonate and provisional interpretation. Its plot
uses the estimated pair. An incomplete estimated pair has an explanatory message and retains available numbers; no point is fabricated from derived source coordinates.

Plots share pH x-limits initially 7.0–7.8 and CO2 y-limits initially 20–80 mmHg, expanded with
8% padding where necessary to include points and Farkas endpoints. The shared reference cross
is pH 7.40 / CO2 40 mmHg, with higher/lower axis descriptions rather than diagnoses. It is not
a validated venous normal boundary. Farkas has a vertical agreement whisker only; fixed estimates
have no whisker. SVGs use distinct markers, direct labels, captions and equivalent accessible
text. Rendering does not compute inference.

Next-input descriptions first request missing measured pH/PvCO2, including when HH completed an axis, then peripheral-appropriate saturation, chemistry, and direct arterial measurements if space remains. They do not request questionnaire fields or BE when calculable. This deterministic
interface order is not a clinically validated information-gain ranking.

The bottom formulas/evidence details remain expandable. The duplicate top warning is removed;
research/privacy wording is consolidated in the footer. Method-specific caveats remain with estimates.

## Synthetic examples

Measured pH 7.32 and PvCO2 55 mmHg give estimated arterial pH 7.36 and PaCO2 50 mmHg, modeled
arterial HCO3 approximately 28.25585 mmol/L, and a provisional compensation assessment. Venous
HH HCO3 remains approximately 28.34661 mmol/L and calculated venous SBE approximately 2.56340.
Selecting Peripheral and adding saturation 75% changes only PaCO2 to 51.04, with agreement endpoints 41.84 and 59.78 mmHg;
modeled bicarbonate and the provisional assessment are then recomputed from that estimated pair.

[Request](examples/request-v5.json) and [result](examples/result-v5.json) are synthetic fixtures
from the public entry point. The browser has no export or persistence feature.


## v5 interpretation and display metadata

`input_observations` records warning policy ID, source field, normalized value (null for
normalization overflow), inclusive limits, and whether axis interpretation is suppressed.
Finite calculations retain their own availability. Every dependent lane checks AVAILABLE before
reading values; outside-scope, missing, unreliable and domain failures propagate locally.

`physiology_direction` records the named model, sample type, assumption, per-axis status/bound,
permitted coordinate categories, display-bound precision note, summary and limitations. Only
usable measured axes supply bounds; no JS classification or viewport-based inference is allowed.
The exact caption is “Conditional arterial direction under usual tissue transit; not a confidence
region or guaranteed ABG bound.” Unknown adds “Sample type not specified.” Short-dashed equality guides,
light hatching, open continuation arrows and markers above the overlay distinguish these marginal
directions from the dashed reference cross. CO2 viewports never extend below zero; continuation
arrows stop at a zero bottom. No probability or joint attainability is assigned.

`interpretation_sensitivity` carries lower/point/upper examples with fixed estimated pH,
recomputed HH HCO3, pinned Boston assessments and stable primary/compensation categories.
Statuses: CHANGES, NO_CHANGE_TESTED, INCOMPLETE, NOT_QUANTIFIED, or a dependent unavailable status.
No change wording is qualified: “No change in the tested CO₂ scenarios; pH uncertainty and full
robustness remain unassessed.” The best-guess narrative carries this result, unresolved context,
model disagreements and any supported BMP comparison. The second paragraph uses physiology
metadata, with assumptions explicit. Edit/reset clears both paragraphs, observations, plots and
sensitivity; stale asynchronous responses cannot restore them.

Python retains full precision. Display pH uses two decimals and gas/chemistry/BE one, except
scientific notation for extreme values and extra precision plus a note near category boundaries.
The same JavaScript formatter serves cards and plots. Golden sensitivity: peripheral pH7.21,
PvCO2 29, saturation75 gives pHa7.25 and CO2 [15.84,25.04,33.78]; HH [6.948539853,
10.984307949,14.818287641]; Winter comparisons [BELOW,WITHIN,ABOVE], tolerance 1e-6.
