# Interpretation specification

## Request 4.0

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
unknown. There is no specimen, draw-site, adverse-context, supplemental-oxygen or separate
same-sample questionnaire. Applicability is not assessed. Chemistry timing remains explicit.

## Result 4.0

The root contains schema/software versions, input summary, venous gas, chemistry, screening,
`arterial_ph_estimate`, `arterial_paco2_estimate`, `modeled_arterial_hco3`,
`provisional_interpretation`, unresolved questions, at most three next inputs, and methods.
Venous gas retains measured values in original units, calculated coordinates, numerical
consistency, measured-pH reference position, and venous SBE. A supplied PCO2 entry additionally
has `normalized_mmhg` when normalization succeeds, for the measured coordinate display.

Each calculation carries status, values, units, input origins, output provenance, method ID,
evidence tier, limitations, missing inputs, and optional applicability. Statuses are AVAILABLE,
UNAVAILABLE_MISSING_INPUT, UNAVAILABLE_OUTSIDE_SCOPE, or MODEL_DOMAIN_REFUSAL. Unavailable
calculations have no numeric values. Screening remains NOT_CONFIGURED.

The provisional interpretation carries its own status, assessment, missing inputs, limitations,
method ID and provenance. Its assessment is the pinned Boston helper's structured result with
`modeled_vs_expected` replacing `measured_vs_expected`, and wording adapted for estimated inputs.
No chemistry/SBE operands are fabricated to call that gas-only helper. Chronic emphasis is disabled;
this does not establish an acute process. The helper's broad acute/chronic comparisons remain.

## Estimate selection and independent outputs

- Measured venous pH alone supports estimated arterial pH = pH + 0.04.
- Measured PvCO2 alone supports estimated PaCO2 = PvCO2(mmHg) − 5.
- Adding same-sample venous saturation selects Farkas: PvCO2 − 0.22 × (93 − saturation%).
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
uses only a finite measured venous pair, with pressure normalized by Python. “Best guess” shows
estimated arterial coordinates, modeled bicarbonate and provisional interpretation. Its plot
uses the estimated pair. An incomplete pair has an explanatory message and retains available
numbers; no point is fabricated from derived source coordinates.

Plots share pH x-limits initially 7.0–7.8 and CO2 y-limits initially 20–80 mmHg, expanded with
8% padding where necessary to include points and Farkas endpoints. The shared reference cross
is pH 7.40 / CO2 40 mmHg, with higher/lower axis descriptions rather than diagnoses. It is not
a validated venous normal boundary. Farkas has a vertical agreement whisker only; fixed estimates
have no whisker. SVGs use distinct markers, direct labels, captions and equivalent accessible
text. Rendering does not compute inference.

Next-input descriptions first offer saturation to switch methods, then needed measured gas
coordinates, then the nearest chemistry calculation, then direct arterial measurements if space
remains. They do not request questionnaire fields or BE when calculable. This deterministic
interface order is not a clinically validated information-gain ranking.

The bottom formulas/evidence details remain expandable. The duplicate top warning is removed;
research/privacy wording is consolidated in the footer. Method-specific caveats remain with estimates.

## Synthetic examples

Measured pH 7.32 and PvCO2 55 mmHg give estimated arterial pH 7.36 and PaCO2 50 mmHg, modeled
arterial HCO3 approximately 28.25585 mmol/L, and a provisional compensation assessment. Venous
HH HCO3 remains approximately 28.34661 mmol/L and calculated venous SBE approximately 2.56340.
Adding saturation 75% changes only PaCO2 to 51.04, with agreement endpoints 41.84 and 59.78 mmHg;
modeled bicarbonate and the provisional assessment are then recomputed from that estimated pair.

[Request](examples/request-v4.json) and [result](examples/result-v4.json) are synthetic fixtures
from the public entry point. The browser has no export or persistence feature.
