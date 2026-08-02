# Architecture

## Product shape

The repository contains one application:

```text
current VBG + current BMP/CMP + optional context + one optional prior observation
                                      ↓
                          VbgExplorerRequest
                                      ↓
                       vbg_interpreter.interpret_vbg
                                      ↓
                          VbgExplorerResult
                                      ↓
                   static client-side Explorer browser
```

The result has independent observed-VBG, candidate-region, state-space, chemistry, and
longitudinal lanes. The final result synthesizes their limitations and typed information needs
without flattening provenance. Every serialized result records the Explorer software version;
the deployed bundle separately records the exact source commit.

## Source ownership

- `src/vbg_interpreter/models.py` contains the single typed request/result contracts.
- `normalize.py` converts only explicit input units at the boundary.
- `candidate_region.py` owns the gated Farkas pH–PaCO₂ sensitivity region.
- `certified_envelope.py`, `state_categories.py`, and `state_space.py` own exhaustive compatibility
  ruleset enumeration and set predicates.
- `chemistry.py` owns serum chemistry and its narrow adapter to the upstream structured Stewart
  partition.
- `longitudinal.py` retains prior observations without changing current modeled state space.
- `interpret.py` is the one public composition entry point.
- `mapping.py` and `browser_adapter.py` define the strict browser boundary.

The upstream compatibility baseline was `d2b25089f998748a91abfea14c68c23ac9eed708`. The external
`stewartlight` dependency is pinned in `pyproject.toml` and `uv.lock` to its descendant
`f277cac54801d85366cbadbf11804f6643f6a869`, which adds the extracted structured Stewart
partition helper and its specimen-neutral input. That upstream change was tested against frozen
legacy ABG payload fixtures; the Explorer calls no upstream browser, narrative, or full-result
surface. The Explorer does not ship a second editable ABG implementation.

## Static browser build

`scripts/build_web.py` creates ignored `.build/web/` from source `web/` and stages exactly two
installed pure-Python packages: `vbg_interpreter` and the pinned `stewartlight`. It writes a
canonical package manifest and a release manifest. GitHub Pages passes the
reviewed source commit into the build, and the release manifest exposes that exact binding. Local
builds are explicitly marked unbound. The Pyodide worker accepts only same-origin assets, mounts the staged
packages under its own filesystem root, and imports the single browser adapter.

Browser JavaScript may validate form shape and render typed results, but the Python mapping and
interpreter are authoritative. Browser code does not reconstruct scientific classifications from
prose or infer values independently.

## Privacy and security boundary

The static app has a restrictive same-origin content-security policy. It has no application
backend, URL state, browser storage, telemetry, or entered-value export. The self-hosted Pyodide
vendor is verified by `scripts/verify_pyodide_vendor.py`.

GitHub Pages deployment is allowed only from `reblocke/VBG_interpreter` while the repository's
live API visibility is public. The deployment workflow re-runs the complete local verification and
synthetic matrix, uploads only `.build/web`, and uses pinned action commits. The private development
history is preserved in a separate private archived repository; the public repository begins with
one reviewed, history-free source commit.

## Verification

`make test` runs focused Python/browser-contract tests. `make validation` runs a deterministic
synthetic scientific matrix. `make e2e` exercises the static browser. `make verify` checks
formatting, lint, the vendor runtime, tests, the generated bundle, and E2E behavior. CI retains
the required `verify` and `validation` job names.
