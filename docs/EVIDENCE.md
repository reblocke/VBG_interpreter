# Evidence and provenance

This record describes the v0.5 research/educational contract. Passing synthetic checks does not
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

## Arterial estimates and provisional interpretation

The owner selected rough point corrections on 2026-09-12: arterial pH = measured venous pH +0.04,
and PaCO2 = measured PvCO2 −5 mmHg unless the sample is explicitly peripheral with supplied same-sample saturation. These exact offsets are product
heuristics, not claims that population agreement establishes an individual correction. Byrne AL
et al. Peripheral venous and arterial blood gas analysis in adults: are they comparable?
*Respirology*. 2014;19:168–175. [doi:10.1111/resp.12225](https://doi.org/10.1111/resp.12225)
reports a pooled pH difference near 0.03 and variability in CO2 agreement. That literature is
context for limitations, not validation of this combined algorithm. No individual fixed-offset
uncertainty range is supplied.

With an explicitly peripheral sample and unit-explicit same-sample venous saturation, the PaCO2 method becomes:
`estimated PaCO2 = measured PvCO2 − 0.22 × (93 − venous saturation%)`.
This replaces the −5 correction; pH retains +0.04. The component is
`farkas_simplified_93_v1`, described in the Farkas public manuscript and evaluated by Jörg M,
Öster M, Wretborn J, Wilhelms DB. Agreement of pCO2 in venous to arterial blood gas conversion
models in undifferentiated emergency patients. *Intensive Care Medicine Experimental*.
2023;11:80. [doi:10.1186/s40635-023-00564-w](https://doi.org/10.1186/s40635-023-00564-w).

The study used upper-extremity peripheral sampling. The v0.5 form records only Peripheral / Central / Unknown and restricts Farkas to explicit peripheral samples. It does not assess perfusion, treatment changes, preanalytic issues or supplemental oxygen. All applicability is
explicitly unassessed. Same-sample meaning belongs to the saturation field itself; no extra
confirmation is required. The conservative published oxygen-profile estimate-minus-arterial
errors −8.74 to +9.20 mmHg produce the range [estimate −9.20, estimate +8.74]. It is population
agreement, not individual confidence or a jointly validated pH/CO2 region. Nonpositive or
nonfinite point/range values cause local refusal without clamping or fallback. Saturation above
93% retains the model-reference caveat. SpO2/PO2 and derived PvCO2 are not model inputs.

Modeled arterial HCO3 uses the same retained HH constants applied to the estimated pH/PaCO2 pair.
Reported or derived venous HCO3 remains separate. The pinned `stewartlight@f277cac` Boston helper
receives only the estimated pH, PaCO2, modeled HCO3 and disabled chronic emphasis through a
structural adapter; no SBE or chemistry is fabricated. Its existing thresholds and compensation
rules are preserved. An explicit adapter recognizes only pinned primary labels and comparison templates; unknown templates refuse interpretation. Only the comparison source attribution becomes “modeled,” and the output is labeled provisional. Structured expected values remain unchanged. Disabling chronic emphasis does not establish acuity; the broad acute/chronic
comparisons are retained. No arterial SBE or new compensated-state enumeration is computed.

External evaluation applies only to the PaCO2 component, not the fixed pH heuristic, derived
HCO3, provisional assessment, patient-specific coverage, or the combined workflow. Screening
remains NOT_CONFIGURED. Software oracle/fixture checks are not clinical validation.

The coordinate plots display measured versus estimated points; they do not infer diagnoses.
The pH 7.40 / CO2 40 mmHg reference cross is a common descriptive coordinate, not a validated
venous decision boundary. A vertical Farkas whisker is not an arterial confidence rectangle.

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
Population agreement summaries are context only. They are not used as individual validated
conversion coefficients or to construct a joint arterial region in v0.5.

Source equations and bibliographic records were checked for this change on 2026-09-12. No
article, table, figure, standard, patient dataset, or publisher layout is distributed. Existing
Farkas, Jörg, Bloom, Krbec, and CLSI provenance/rights notices remain in THIRD_PARTY_NOTICES.md.

## Verification boundary

The synthetic matrix checks arithmetic targets, units, gate decisions, provenance, local-domain
refusals, independent partial results, partition closure, and deterministic contracts. Browser
checks exercise the self-hosted runtime, privacy, accessibility, and progressive rendering.
No validated local end-to-end VBG algorithm exists. Screening, prediction, compensation
classification, and management equivalence remain separate scientific claims.


## Conditional physiology

`usual_tissue_transit_direction_v1` is an owner-selected simplified model, not an externally
validated individual bound: given a comparable systemic venous sample and usual steady-state
tissue transit, assume arterial pH ≥ measured venous pH and 0 < PaCO2 ≤ measured PvCO2.
The magnitude is unidentified. Both peripheral and central samples may show this conditional
model; Unknown adds an illustrative systemic-venous assumption and explicit unknown caption.
Neither sample selection nor a single gas verifies applicability. Content exchange alone does
not prove universal tension/pH inequalities: mixing, oxygenation, chemistry, timing, perfusion,
local metabolism and measurement can invalidate them. No joint attainability or likelihood is
assigned to the two marginal directions. Unshaded space is not clinically ruled out.

Timing and central-gradient context: [Shastri et al., DOI 10.1007/s10877-021-00764-3](https://doi.org/10.1007/s10877-021-00764-3)
reported differing arterial/peripheral responses after transient ventilation changes;
[Mallat et al., DOI 10.1186/s13613-017-0258-5](https://doi.org/10.1186/s13613-017-0258-5)
studied ventilation-related changes in central venous-to-arterial CO2 difference. These support
limitations, not a universal gradient sign, central Farkas validation or a new conversion rule.

The pH half-line is intersected with <7.35, [7.35,7.45], >7.45 at full precision. CO2 categories
refer only to below/equal/above the display cross at 40 mmHg. Coordinate possibilities do not
establish chronicity, exclude metabolic-acidosis components or relative respiratory acidosis,
or identify a unique primary process. No upper pH or positive minimum CO2 is inferred.
HH-derived axes cannot supply independent bounds. Plot limits never enter these predicates.

The peripheral Farkas range is kept independent, even when its point or upper endpoint exceeds
PvCO2; disagreement is described without clipping. Lower/point/upper sensitivity examples hold
estimated pH fixed, recalculate HH, and reuse unchanged pinned Boston rules. These are not
exhaustive, joint, probabilistic or full robustness analyses. Fixed offsets have no sourced
individual sensitivity range. Any failed scenario makes sensitivity incomplete.

## Input observations and bicarbonate comparison

`input_sanity_v1` is an owner-selected software warning policy, not clinical reference limits.
Inclusive normalized intervals: pH 6–8.5; PvCO2 5–250 mmHg; gas and BMP HCO3 1–100 mmol/L;
sodium 80–220; chloride 40–200; lactate 0–40; reported BE −60–60 (all mmol/L); albumin 0–80 g/L.
Finite values outside these intervals remain visible; no correction, unit guessing or confirmation
is performed. A warned pH/PvCO2 axis is withheld from physiology and dependent whole-gas prose.
Other usable axes and independent finite arithmetic remain. No second severe-input threshold exists.

Albumin normalization uses explicit g/dL ×10 or g/L unchanged, preserving the original unit/value.
BMP–gas difference = chemistry total CO2 − venous gas-basis HCO3. Prefer HH from usable measured
pH/PvCO2 even if a third gas HCO3 was supplied; otherwise use supplied actual gas HCO3 supporting
an alternate completed pair. Unsupported basis gives partial output. Display timing and basis.
Absolute difference >10 mmol/L is a warning heuristic, not a diagnostic rule. Gas-only prose does
not reconcile chemistry. External actual versus standardized bicarbonate cannot be identified
from the number alone; help text explains the intended input. No new source formula was copied.
