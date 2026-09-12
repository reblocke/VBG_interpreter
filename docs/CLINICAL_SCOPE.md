# Clinical scope

Version 0.5.0 is the current public research preview. It presents reported venous measurements,
algebraic calculations, serum chemistry, and caveated arterial estimates with a provisional compensation assessment. It is not
clinically validated, not medical advice, and not a medical device. It must not be used to
diagnose, treat, triage, or replace an arterial blood gas when arterial confirmation is required.
Use synthetic values only; do not enter PHI or real patient data.

## Evidence boundaries

- A single VBG value can be reported without completing a gas. At least two appropriate gas
  coordinates enable HH completion. Completed coordinates remain venous and explicitly derived.
- The 7.35–7.45 pH comparison is a retained descriptive reference band. It is not a validated
  venous normal interval or an arterial acidemia/alkalemia classification.
- Reported-versus-HH HCO3 difference is numerical consistency information without a clinical
  discordance cutoff. Reported HCO3 provenance may be unknown.
- Calculated venous SBE uses the selected standardized Van Slyke equation with normothermia
  (37°C) assumed. It is not arterial SBE, actual whole-blood BE, or an analyzer-equivalence claim.
  It inherits the provenance of its pH and blood-gas HCO3 operands. A reported actual/unknown BE
  is echoed but never relabeled as standard BE.
- Fixed arterial estimates use the owner-selected pH +0.04 and PvCO2 −5 mmHg heuristics.
  These are rough point estimates, not individual validated conversions or intervals.
- Same-sample venous saturation with explicitly peripheral sample type selects Farkas for PaCO2, while pH keeps its
  fixed correction. SpO2 and PO2 are not accepted substitutes. Only measured source coordinates
  enter the models; HH-derived venous coordinates do not become independent measurements.
- Only Peripheral / Central / Unknown sample identity is collected; perfusion, treatment-change and preanalytic context are not collected. Every
  estimate is labeled applicability-unassessed; the app does not establish favorable conditions.
- Farkas retains the conservative published oxygen-profile agreement bounds. They are not
  patient-specific probability intervals, and do not establish joint pH/CO2 coverage. Invalid
  endpoints are refused without clamping or silently reverting to the fixed method.
- Modeled arterial HCO3 is calculated from the estimated pair, separately from venous HCO3.
  The provisional Boston output describes compatibility at that point, not confirmed diagnosis,
  exclusions or chronicity. The combined pH/CO2/interpretation path has no external validation.
- Matching measured/estimated plots are explanatory. Their pH 7.40 / CO2 40 reference cross
  is not a validated venous cutoff or diagnostic partition. Missing pairs have no invented point.
- Serum total CO2 is distinct from blood-gas HCO3. AG and albumin-corrected AG are numerical
  calculations without universal laboratory-normal thresholds. Na−Cl is a descriptive surrogate.
- Venous Stewart partition requires measured venous pH, reported or calculable venous SBE,
  Na, Cl, albumin, and an explicit same-timepoint relationship. Lactate is optional. Calculated
  SBE remains a derived operand in the partition and carries its normothermia limitation.
- Categorical PvCO2 screening is not configured. Screening, prediction, compensation
  classification, and management equivalence are separate claims.

## Unavailable inferences

The app does not infer arterial oxygenation, PaO2, A–a gradient, P/F ratio, tissue
hypoxia, oxygen extraction, arterial SBE, or a definitive arterial acid–base state. Chemistry cannot
supply current PaCO2. Missing data or a failed numerical calculation cannot erase independent
available results. Next-input descriptions explain information gained without directing care.

Population agreement summaries do not validate individual conversion or define a joint arterial region.
Prior-observation interpretation was deferred in v0.3; its removal does not disprove the value
of appropriately studied longitudinal information.

## Privacy and public availability

Calculations are static, client-side, and nonpersistent. No entered values enter URLs, logs,
telemetry, browser storage, exports, or a calculation backend. Initial asset requests are ordinary
same-origin HTTPS requests and may have hosting/security logs without entered form values.

No validated local end-to-end VBG algorithm exists. Software checks and the public research
preview do not establish clinical performance, approval, intended clinical use, or management
safety. Source and Pages publication remains bound to the same reviewed commit.


Conditional tissue-transit shading is an illustrative model with unverified assumptions, not a
guaranteed individual bound, confidence region or diagnosis heatmap. Central and peripheral may
show it; Unknown explicitly labels the systemic-venous assumption. Unshaded space is not ruled
out. Deterministic CO2 sensitivity tests three examples, holds pH fixed, and establishes neither
probability nor full robustness. Input sanity and >10 mmol/L BMP–gas discrepancy warnings are
software heuristics, not diagnostic thresholds; no confirmation or clinical questionnaire is added.
