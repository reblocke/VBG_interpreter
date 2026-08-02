# Changelog

## Unreleased

No unreleased changes.

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
