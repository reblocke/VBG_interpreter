# ADR 0008: Dependency warnings and concise output

Date: 2026-09-14. Status: accepted by the owner for v0.6.1 implementation.

This decision supersedes ADR 0007's bicarbonate-warning exception. Existing software sanity
intervals apply to finite HH-reconstructed venous coordinates as well as supplied values.
Observations identify coordinate origin and original source fields. They are software checks,
not new clinical thresholds, and never correct an entered or calculated value.

Finite arithmetic remains available. A warning on an actually consumed operand or reconstructed
coordinate withholds dependent provisional interpretation, sensitivity, and the estimated paired
plot. Independent supplied axes remain eligible for measured direction shading. A flagged,
unused reported bicarbonate does not taint estimates from supplied pH/PvCO2 or the SBE calculation
that preferentially uses their HH bicarbonate. Reported standard BE still takes precedence.
Numerical failure retains its domain-refusal status rather than being relabeled as a finite
warned result. No new equations, selection rules or agreement intervals are introduced.

Calculation envelopes carry dependency warnings and arterial route labels. Result schema is
6.1; strict request schema remains 5.0, with no compatibility shim. Short summaries retain
structured Boston conclusions and case qualifications; compensation/scenarios and formula-level
evidence remain expandable. Available optional arithmetic stays visible. Missing numerical
prerequisites move into Additional calculations, while context or numerical refusal with supplied
prerequisites remains visible. Plot geometry, shared scales and independent agreement ranges stay.

Regression fixtures come from the owner's targeted review bundle but execute strict mapping,
real interpretation and serialization, plus the actual Pyodide browser worker. The bundle's
production snapshots and contract doubles are not adopted. Synthetic checks establish software
behavior only; public deployment and direct live browser acceptance are separately recorded.
