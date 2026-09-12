# ADR 0005: Measured facts and provisional best guess

Accepted 2026-09-12; supersedes the estimate selection and output restrictions in ADR 0004.

The owner requested estimated arterial pH +0.04 and PvCO2 −5 mmHg from the measured venous pair,
with optional same-sample venous saturation selecting Farkas for CO2 only. BE remains optional.
The owner selected numbers plus a provisional acid–base interpretation and removal of the
context questionnaire. The field label establishes same-sample saturation; applicability is
unassessed rather than silently favorable. The conservative existing Farkas oxygen-profile
agreement bounds remain, with no fixed-offset or joint uncertainty interval.

A gas-only structural adapter calls the pinned upstream Boston helper. It passes estimated pH,
PaCO2 and their HH bicarbonate without fabricating required fields of the upstream full-app
input. Chronic emphasis is disabled without claiming acuity; existing broad acute/chronic
comparisons are preserved and checked against the upstream full-input oracle. Method wording
identifies modeled operands. No state enumeration or individual exclusion is reintroduced.

The selected axes are pH horizontally and CO2 vertically. Matching measured and estimated
plots share expanded scales and a descriptive 7.40/40 reference cross; they perform no inference.
The measured plot cannot be completed with derived venous coordinates. Farkas alone adds a
vertical agreement whisker. Captions, marker shapes and text equivalents preserve accessibility.

The duplicate top warning is removed; general research/privacy wording is consolidated in the
footer. The formulas/evidence box remains at the bottom. Method-specific caveats remain close
to estimates. Request/result v4 replaces the prerelease v3 contract without a compatibility shim.
No backend, telemetry, storage, URL state or export is introduced. Tests use only synthetic values.

Acceptance includes the 7.32/55 → 7.36/50 regression, 75% saturation → 51.04 mmHg, BE independence,
unit/provenance boundaries, numerical refusals, upstream compensation parity, mobile/keyboard/
400% text behavior, and exact-commit source/Pages verification through normal CI.
