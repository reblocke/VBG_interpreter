# Clinical scope

Version 0.3.0 is the current public research preview. It presents reported venous measurements,
algebraic calculations, serum chemistry, and a narrowly scoped PaCO2 estimate. It is not
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
- The Farkas/Jörg component requires source-measured PvCO2, unit-explicit measured venous
  saturation, and explicit same-sample confirmation. It never uses HH-derived PvCO2.
- Known nonperipheral specimen, non-upper-extremity draw, poor perfusion/hemodynamic instability,
  recent major treatment/ventilation change, or material preanalytic concern withholds the
  estimate. Same-sample NO withholds it; UNKNOWN requires confirmation.
- Unknown specimen/site/clinical context may permit a prominently marked applicability-uncertain
  estimate. Unknown does not become favorable. External evaluation describes the method,
  not proof that the current supplied context is within the evaluated population.
- The displayed agreement range is deterministic, not a patient-specific probability interval.
  Unknown oxygen uses the existing conservative profile. No endpoints are clamped.
- Serum total CO2 is distinct from blood-gas HCO3. AG and albumin-corrected AG are numerical
  calculations without universal laboratory-normal thresholds. Na−Cl is a descriptive surrogate.
- Venous Stewart partition requires measured venous pH, reported or calculable venous SBE,
  Na, Cl, albumin, and an explicit same-timepoint relationship. Lactate is optional. Calculated
  SBE remains a derived operand in the partition and carries its normothermia limitation.
- Categorical PvCO2 screening is not configured. Screening, prediction, compensation
  classification, and management equivalence are separate claims.

## Unavailable inferences

The app does not infer arterial pH, arterial oxygenation, PaO2, A–a gradient, P/F ratio, tissue
hypoxia, oxygen extraction, arterial SBE, or a complete arterial acid–base state. Chemistry cannot
supply current PaCO2. Missing data or a failed numerical calculation cannot erase independent
available results. Next-input descriptions explain information gained without directing care.

Population agreement summaries do not define an individual conversion or joint arterial region.
Prior-observation interpretation was deferred in v0.3; its removal does not disprove the value
of appropriately studied longitudinal information.

## Privacy and public availability

Calculations are static, client-side, and nonpersistent. No entered values enter URLs, logs,
telemetry, browser storage, exports, or a calculation backend. Initial asset requests are ordinary
same-origin HTTPS requests and may have hosting/security logs without entered form values.

No validated local end-to-end VBG algorithm exists. Software checks and the public research
preview do not establish clinical performance, approval, intended clinical use, or management
safety. Source and Pages publication remains bound to the same reviewed commit.
