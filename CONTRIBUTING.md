# Contributing

Contributions that improve correctness, accessibility, documentation, testing, or conservative
scientific communication are welcome.

## Before opening a change

- Read [clinical scope](docs/CLINICAL_SCOPE.md), [interpretation semantics](docs/INTERPRETATION_SPEC.md),
  [evidence](docs/EVIDENCE.md), and [third-party notices](THIRD_PARTY_NOTICES.md).
- Use only fictional synthetic values. Never add PHI, patient-derived rows, protected paths,
  screenshots from patient care, credentials, or restricted source artifacts.
- Open an issue before changing formulas, coefficients, scope, evidence labels, or set predicates.
- Keep measured, calculated, modeled, chemistry, and historical values structurally distinct.
- Do not introduce diagnosis, treatment, ABG-substitution, probability, or clinical-validation
  claims.

## Development workflow

```bash
uv sync --locked
uv run playwright install chromium
make fmt
make lint
make test
make validation
make e2e
make verify
```

The Python package is the calculation source of truth. Browser assets are generated into ignored
`.build/web/`; do not commit generated Python packages. Follow the [testing policy](AGENTS.md#testing-policy):
prefer E2E coverage, and retain isolated tests only for concrete failures the E2E suite misses.
Write down the failure modes and any necessary unit tests before implementation. Update the
relevant current-state documentation with behavior or workflow changes.

Every `make e2e` run saves `.build/e2e/results.xml` plus a `trace.zip` and screenshot in each test's
subdirectory, including passing tests. Rerun with the locked dependencies and the same command to
reproduce the checks. Inspect a trace with `uv run playwright show-trace .build/e2e/<test-id>/trace.zip`.
The traces contain actions, DOM snapshots, and network activity from synthetic inputs only. This
directory is replaced on the next E2E run; `make test` and `make validation` leave it intact.

Pull requests should explain the intended behavior, scientific and privacy boundaries, commands
run, and remaining limitations. A passing test suite confirms implemented behavior; it does not
establish clinical validity.
