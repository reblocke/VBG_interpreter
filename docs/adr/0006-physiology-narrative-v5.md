# ADR 0006: Conditional physiology, sample selection and v5 narrative

Accepted 2026-09-12 through the owner's approved v0.5 implementation plan. Supersedes conflicting
sample-selection and display requirements in ADR 0005; retains its calculations and privacy scope.

Add only Peripheral / Central / Unknown, default Unknown. Farkas needs explicitly peripheral
measured PvCO2 and same-sample saturation. Other identities select the fixed CO2 heuristic and
disclose unused saturation. No failed-Farkas fallback, clinical-context questionnaire or favorable
assumption is introduced. Albumin units are explicit, normalized once and preserved at source.

A named warning-only policy retains unusual finite inputs and arithmetic. The owner clarified that
a warned pH/PvCO2 suppresses that axis's interpretation and dependent whole-gas prose, while the
other usable measured axis retains direction and shading. No second severe threshold is needed.
Other warnings do not suppress independent gas interpretation. Hard structural/domain rules remain.

A small Python direction result is the common source for prose and SVG. Its marginal inequalities
are conditional model assumptions, not universal physiology or a jointly attainable state set.
Singletons show one half-plane and no invented point. Unbounded directions continue beyond the
viewport; positive CO2 is explicit. No symbolic inference framework, rectangle or state engine.

The pinned Boston helper remains numerical authority. A narrow adapter recognizes its existing
primary labels and comparison templates; unknown output refuses locally. Three Farkas scenarios
recompute HH at fixed estimated pH and compare stable categories. Unchanged examples do not prove
full robustness. Fixed offsets have no sourced interval. All dependent statuses are checked before
value dereferences; finite arithmetic is separate from interpretation suitability.

BMP-minus-gas bicarbonate is descriptive with basis and timing, preferring HH from the measured
pair, otherwise supplied gas bicarbonate in an alternate completed pair. >10 mmol/L absolute
mismatch is a warning heuristic. Gas-only interpretation cannot reconcile serum chemistry.

Five reviewable areas: inputs/observations; conditional directions/summary; sensitivity/status/
chemistry; shading/formatting; validation/docs/publication. Verification includes synthetic golden
examples, exact thresholds, upstream oracle, all failure statuses, unit equivalence, real Pyodide,
responsive/forced-color views and stale-result/privacy checks. Public availability adds no clinical
validation. Version/schema bump is deliberate with no pre-release compatibility shim.
