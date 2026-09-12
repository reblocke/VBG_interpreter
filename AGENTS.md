# VBG Acid–Base Explorer contributor guidance

## Product boundary

This repository contains one public research-preview VBG Acid–Base Explorer. Its Python package is
`vbg_interpreter`; its static browser source is `web/`; generated browser assets are written only
to ignored `.build/web/` by `scripts/build_web.py`.

The upstream ABG educational application and core belong to
[`reblocke/stewart-light`](https://github.com/reblocke/stewart-light). Do not restore a second ABG
browser workflow or copy an upstream formula already exposed by the pinned dependency.

## Required behavior

- Keep measured venous, modeled arterial, calculated, and serum-chemistry values distinct.
- Return partial results when a dependent lane cannot run; do not make the full request fail.
- Treat unknown model context as unknown, never as favorable context.
- Keep inference capability-based; no population-derived arterial rectangle or state enumeration.
- Keep the Boston point assessment provisional and based only on the estimated arterial pair.
- Do not assign probability meaning to deterministic agreement ranges.
- Keep serum total CO₂ distinct from blood-gas HCO₃. Do not infer current PaCO₂ from chemistry.
- Do not estimate arterial oxygenation, PaO₂, A–a gradient, P/F ratio, tissue hypoxia, oxygen
  extraction, or arterial SBE.
- Keep measured gas coordinates, HH-derived coordinates, calculated venous SBE, and modeled
  arterial values separate. Only measured source coordinates enter the fixed/Farkas estimates.
- Saturation is same-sample by field definition. Do not restore the clinical-context questionnaire;
  applicability remains explicitly unassessed. BE stays optional.
- Coordinate plots display results only; their reference cross is not a diagnostic boundary.
- Standard BE may be reported or calculated with the approved Van Slyke method at assumed 37°C;
  retain its provenance in venous Stewart output. Actual/unknown BE is not automatically SBE.
- Require measured venous pH and same-time chemistry for the Stewart partition.
- Keep categorical screening NOT_CONFIGURED until an owner-approved sourced threshold exists.

## Privacy and clinical copy

The browser must remain static, client-side, and nonpersistent. Do not add a backend, telemetry,
browser storage, URL state, patient-value logs, exports, or real/patient-derived examples. Keep
all user-facing language research/educational, conservative, and free of diagnosis or treatment
directives. Do not enter PHI while testing.

The public repository and Pages site must be built from the same reviewed commit. Changes to
deployment, public wording, scientific formulas, provenance, or privacy boundaries require focused
tests and synchronized documentation. Public availability is not clinical validation.

## Change discipline

Before a nontrivial change, state the intended behavior, ambiguity, safety risks, files affected,
and verification. Prefer the smallest focused change. Do not add migrations or compatibility
shims for superseded pre-release Explorer schemas.

Use these local skills where applicable:

- `implementation-strategy` before nontrivial work;
- `scientific-validation` for formulas, state enumeration, or scientific figures;
- `clinical-scope-review`, `privacy-no-phi-review`, and `public-copy-safety-review` for their
  respective surfaces;
- `static-browser-pyodide-verification` when changing the browser, worker, staging, or vendor;
- `docs-sync` after behavior or commands change; and
- `code-change-verification` before handoff.

## Commands

```bash
uv sync --locked
make fmt
make lint
make test
make validation
make e2e
make verify
make serve
```

`make verify` is the normal full local check. It stages the browser bundle, verifies the
self-hosted Pyodide runtime, runs focused Python tests, and runs browser E2E smoke tests.
