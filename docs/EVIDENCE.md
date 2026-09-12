# Evidence and provenance

This record describes the v0.3 research/educational contract. Passing synthetic checks does not
validate the full Explorer, establish analyzer equivalence, or support clinical management.

## Venous gas and standard base excess

Supplied pH and PvCO2 are source measurements. Blood-gas HCO3 has independent reported/calculated/
unknown provenance. HH completion uses the retained constants `0.0307` and `6.095`:

`HCO3 = 0.0307 × PvCO2(mmHg) × 10^(pH − 6.095)`.

Its inverses complete only a missing gas coordinate. `MEASURED_OR_REPORTED` and
`CALCULATED_HENDERSON_HASSELBALCH` are different origins. Supplied HCO3 is never overwritten;
all-three inputs yield a neutral signed reported-minus-HH HCO3 difference. The retained
7.35–7.45 comparison is descriptive, not a validated venous reference interval.

The owner selected the classic standardized Van Slyke equation on 2026-09-12:

`SBE = 0.9287 × [HCO3 − 24.4 + 14.83 × (pH − 7.4)]` (mmol/L).

Source: Schlichtig R, Grogono AW, Severinghaus JW. Human PaCO2 and standard base excess
compensation for acid-base imbalance. *Critical Care Medicine*. 1998;26(7):1173–1179.
[doi:10.1097/00003246-199807000-00015](https://doi.org/10.1097/00003246-199807000-00015).
The methods specify standardized effective hemoglobin of 3.1 mmol/L (approximately 5 g/dL) and
HH completion at 37°C. This app uses its retained HH constants rather than changing them to the
paper's rounded constants. That implementation choice is explicit and tested; no compensation
rules from the paper are implemented.

Reported standard BE takes precedence. Otherwise, two gas coordinates support calculated
venous-basis SBE. A measured pH/PvCO2 pair uses its HH bicarbonate even if a third HCO3 was
reported; pH/HCO3 uses the supplied pair, and PvCO2/HCO3 uses explicitly HH-derived pH.
Actual/unknown BE is never silently substituted for standard BE. Serum total CO2 and modeled
arterial PaCO2 are not operands. Normothermia (37°C) is assumed and displayed. SBE is a derived
calculation with method ID `venous_sbe_van_slyke_37c_v1`, not a measured or arterial value.
No actual-Hb, temperature-correction, corrected-SBE, or analyzer-matching model is added.

## PaCO2 component

`estimated PaCO2 = measured PvCO2 − 0.22 × (93 − same-sample venous saturation%)`.

The component is `farkas_simplified_93_v1`, originally described in the Farkas public manuscript
and externally evaluated by Jörg M, Öster M, Wretborn J, Wilhelms DB. Agreement of pCO2 in venous
to arterial blood gas conversion models in undifferentiated emergency patients. *Intensive Care
Medicine Experimental*. 2023;11:80.
[doi:10.1186/s40635-023-00564-w](https://doi.org/10.1186/s40635-023-00564-w).

Retained estimate-minus-arterial errors (mmHg) are −5.83 to +5.32 without oxygen and −8.74 to
+9.20 with oxygen. The deterministic arterial-reference range is therefore
`[estimate − upper_error, estimate − lower_error]`. Unknown oxygen selects the latter existing
conservative profile and is labeled unknown. Numerical endpoints must be finite and positive;
there is no clamping. Saturation above 93% retains a model-reference caveat.

The study sampled upper-extremity peripheral veins. Full eligibility requires that specimen/site
and explicit NO for the three documented adverse-context flags. Known incompatible context
withholds the estimate. Unknown context can produce `APPLICABILITY_UNCERTAIN`, which is not
proof of applicability. Explicit same-sample confirmation remains mandatory. No threshold for
hemodynamics, sampling delay, or treatment recency is invented.

The externally evaluated label belongs only to the PaCO2 component; it does not validate
arterial pH, a derived PvCO2 input, a combined algorithm, patient-specific interval coverage, or
management equivalence. There is no configured categorical screening threshold.

## Serum chemistry

- Serum AG: `Na − Cl − serum total CO2`.
- Albumin-corrected AG: `AG + 0.25 × (40 − albumin g/L)`, retaining the existing correction.
- Na−Cl difference: direct subtraction, a descriptive strong-ion surrogate.

These are explicit arithmetic methods without imputation or high/normal/low thresholds.
Laboratory reference intervals vary. Serum total CO2 remains a chemistry operand only.
Lactate is displayed as measured chemistry and may enter an otherwise eligible partition.

The venous Stewart partition delegates unchanged formulas to the structured helper in
[`stewartlight@f277cac`](https://github.com/reblocke/stewart-light/tree/f277cac54801d85366cbadbf11804f6643f6a869).
It requires source-measured venous pH, reported or calculated venous SBE, Na, Cl, albumin, and
same-clinical-timepoint confirmation. Derived pH cannot enable it. Calculated SBE carries its
full input provenance and normothermia assumption into the partition. The upstream helper's
documentation describes supplied SBE; use of an explicitly derived SBE is this Explorer's
owner-approved adaptation. Its numerical closure is software evidence, not clinical validation.

## Population context and source rights

Bloom BM, Grundlingh J, Bestwick JP, Harris T. The role of venous blood gas in the Emergency
Department: a systematic review and meta-analysis. *European Journal of Emergency Medicine*.
2014;21(2):81–88. [doi:10.1097/MEJ.0b013e32836437cf](https://doi.org/10.1097/MEJ.0b013e32836437cf).
Population agreement summaries are context only. They are not used as individual arterial
conversion coefficients or to construct a joint arterial region in v0.3.

Source equations and bibliographic records were checked for this change on 2026-09-12. No
article, table, figure, standard, patient dataset, or publisher layout is distributed. Existing
Farkas, Jörg, Bloom, Krbec, and CLSI provenance/rights notices remain in THIRD_PARTY_NOTICES.md.

## Verification boundary

The synthetic matrix checks arithmetic targets, units, gate decisions, provenance, local-domain
refusals, independent partial results, partition closure, and deterministic contracts. Browser
checks exercise the self-hosted runtime, privacy, accessibility, and progressive rendering.
No validated local end-to-end VBG algorithm exists. Screening, prediction, compensation
classification, and management equivalence remain separate scientific claims.
