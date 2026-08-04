# Changelog

## [0.2.0] - 2026-08-04

Second public research preview, published from the history-free repository and deployed from the
same reviewed source commit through the commit-bound Pages workflow.

### Breaking contract update

- Replaced `vbg_explorer_request/1.0` and `vbg_explorer_result/1.0` with the sole v2 schemas;
  no migration or compatibility shim is provided.
- Replaced the mandatory pH/PvCO₂-plus-chemistry workflow with a minimum of any two pH, PvCO₂,
  and blood-gas HCO₃ values. Chemistry is now field-by-field optional.

### Changed

- Added supplied-versus-Henderson–Hasselbalch-derived venous-gas origins, an all-three HCO₃
  discrepancy flag, and descriptive venous pH orientation that is not a Boston classification.
- Added the generic Bloom-derived pH/PaCO₂ published-study-level agreement-extrema scenario
  envelope. It uses source-average point orientation only and does not claim individual conversion,
  prediction, confidence, probability, or joint pH–PaCO₂ coverage.
- Retained Farkas/Jörg only as a fully gated PaCO₂-component upgrade; generic pH remains the pH
  component for every available candidate region.
- Added typed unknown-applicability warnings, derived-axis limitations, and no-clamp model-domain
  refusals so a truncated scenario envelope cannot manufacture exclusions.
- Added progressive serum chemistry: anion gap requires supplied sodium/chloride/serum total CO₂,
  and albumin/Stewart context remain independently gated.
- Added ADR 0003 and synchronized public evidence, scope, architecture, and attribution records.

## [0.1.0] - 2026-08-02

First public research preview, published from a history-free repository after the private
development history was preserved separately.

### Breaking pre-release reset

- Replaced the former ABG/VBG multi-product application with one VBG Acid–Base Explorer.
- Replaced all former request/result versions with `vbg_explorer_request/1.0` and
  `vbg_explorer_result/1.0`; no migration or compatibility shim is provided.
- Removed the local editable Stewart Light ABG application and use a pinned upstream
  `stewartlight` dependency for the specimen-neutral structured venous-basis partition helper.
- Replaced finite-grid inference with certified terminal-path enumeration for candidate state sets.
- Replaced protected-data validation, release-authorization, public-export, and historical
  milestone machinery with focused synthetic verification.
- Replaced the browser with one progressive, client-side VBG workflow and self-hosted Pyodide
  build path.

This reset and public release do not create new clinical evidence, authorize clinical use, or
support VBG–ABG interchangeability claims.
