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

## Result 6.0

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

| Supplied pH / PvCO2 / gas HCO3 | Resolved arterial capability |
| --- | --- |
| None (BE or saturation only) | Neither coordinate |
| pH only | pH +0.04 |
| PvCO2 only | CO2 estimate only |
| HCO3 only | Neither coordinate |
| pH + PvCO2 | Both; venous HH HCO3 separate from modeled arterial HCO3 |
| pH + HCO3 | HH-reconstruct PvCO2; both estimates, labeled chained |
| PvCO2 + HCO3 | HH-reconstruct pH; both estimates, labeled chained |
| All three | Supplied pH/PvCO2 precedence; preserve third value and consistency |

Resolved pH uses +0.04. Resolved PvCO2 uses −5 without saturation or for Central; saturation
selects Farkas for Peripheral and conditionally Unknown: PvCO2 −0.22 × (93 − saturation%).
Unknown stays Unknown and states the peripheral assumption. Central explains the fixed route.
Zero saturation is present; malformed/out-of-range saturation remains a typed input error.
No pH, chemistry or BE prerequisite applies to the independent CO2 component.

Each arterial calculation has a typed `selection`: source coordinate origin
(SUPPLIED/HH_RECONSTRUCTED/UNAVAILABLE), normalized source value and status, source field IDs,
original source values/units/basis, derivation method, entered sample type, model scope, reason
codes, case evidence and interpretation suitability. Calculation `status` is point status and
`method_id` is the selected method. Formula `evidence_tier` never implies case validation.
Other calculations have null selection/agreement fields. `source_pvco2` replaces the formerly
measured-only values key; it is not intrinsically a measured coordinate.

The separate `agreement` record has AVAILABLE/NOT_QUANTIFIED/UNAVAILABLE status, reason,
units, and nullable endpoints. No endpoints remain in point `values`. Supplied-PvCO2 Farkas
comparison is [point −9.20, point +8.74], reversing published estimate-minus-reference errors
[−8.74,+9.20]. Positive finite points survive invalid endpoints. Nonpositive/nonfinite points
are refused locally, preserving selected method; no clipping or fixed fallback occurs.
Reconstructed PvCO2 has no evaluated interval. Reconstructed pH retains independently supported
CO2 agreement. Unknown ranges are peripheral-study context under an unconfirmed assumption.
Sensitivity explicitly checks agreement availability; no range means NOT_QUANTIFIED, unless
a required pair is itself unavailable. Available scenarios hold estimated pH fixed, including
reconstructed pH, and recompute HH at each CO2 value.

Only absent axes may be reconstructed with retained HH constants, using actual same-gas HCO3.
Supplied coordinates are never overwritten; BMP HCO3 and BE cannot reconstruct gas coordinates.
All estimates remain applicability-unassessed. Modeled arterial HCO3 uses only the estimated
pair, followed by unchanged pinned Boston rules. A Blood gas HCO3 warning alone does not suppress
finite chained arithmetic, plotting or provisional interpretation; supplied pH/PvCO2 warnings
continue to suppress dependent interpretation and measured directions, including dependent chains.

Reported STANDARD BE (including zero) takes precedence; otherwise existing gas-pair SBE at
37°C applies. Actual/unknown BE is not SBE. Chemistry remains independent; Stewart requires
supplied pH, SBE, same-time Na/Cl/albumin, with optional lactate. BMP–gas comparison prefers HH
from usable supplied pH/PvCO2, otherwise directly supplied actual gas HCO3 without requiring a
completed gas. Finite warned bicarbonates retain subtraction and the existing >10 warning.

## Displays and additional information

“What’s known” contains measurements and separately identified calculations. Its pH × CO2 plot
uses usable measured venous axes, with pressure normalized by Python. A single usable axis shows a half-plane without a point; two axes show lower-right directional shading. “Best guess” shows
estimated arterial coordinates, modeled bicarbonate and provisional interpretation. Its plot
uses the estimated pair. An incomplete estimated pair has an explanatory message and retains available numbers; a suitable HH-derived chain can orient the Best guess plot without adding a measured point or independent bound.

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
Adding saturation 75% with Peripheral or untouched Unknown changes only PaCO2 to 51.04, with agreement endpoints 41.84 and 59.78 mmHg;
modeled bicarbonate and the provisional assessment are then recomputed from that estimated pair.

[Request](examples/request-v5.json) and [result](examples/result-v6.json) are synthetic fixtures
from the public entry point. The browser has no export or persistence feature.


## Interpretation and display metadata

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
