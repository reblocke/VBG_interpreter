# ADR 0009: Prefer E2E coverage and remove redundant isolated tests

Date: 2026-09-24

Status: Accepted

## Decision

Follow the [testing policy](../../AGENTS.md#testing-policy). Prefer browser E2E tests for complex
features. An isolated test needs a concrete failure that existing E2E assertions would miss;
document the failure modes and write necessary unit tests before implementation.

Remove repeated happy paths, copied calculation oracles crossed over thousands of normal input
combinations, exact source-shape checks, documentation snapshots, and hardcoded workflow-version
assertions. A test that compares an implementation with itself does not establish correctness.
Keep product code and scientific formulas unchanged.

## Retained coverage

The browser suite includes real Pyodide workflows and mocked-worker UI scenarios. Mocked results
verify rendering and interaction; they do not establish numerical correctness.

| Isolated checks retained | Concrete gap in the current browser assertions |
| --- | --- |
| Strict Python input rejection | Browser validation prevents malformed requests from reaching the Python boundary. |
| Numerical and unit edge cases | Rendered examples do not check all zero, overflow, inclusive-boundary, or sub-rounding cases. |
| Provenance and independent calculations | Browser output checks do not cover every SBE basis, HH source chain, or dependency-specific warning. |
| Compensation and sensitivity outcomes | Visible scenario summaries do not assert every classification, range, or incomplete-scenario outcome. |
| Privacy source guard | Runtime checks do not exercise every path for cookies, IndexedDB, history state, console logging, or CSP removal. |
| Invalid release-commit rejection | Normal browser builds and successful deployment do not exercise malformed commit bindings. |

Review these exceptions as browser coverage grows. Prefer adding missing behavior to an existing
E2E scenario over retaining a duplicate isolated check. Accessible names for form controls are
checked in the live-worker singleton scenarios, including conditional selectors. Those scenarios
also reject invented coordinates and inappropriate numerical-domain errors for incomplete inputs.

The audit reduced the Python suite from 4,057 to 101 collected cases and retained all 30 browser
cases. The remaining Python cases cover the gaps above; the browser assertions were strengthened
for control names and incomplete inputs.

## Verification and artifacts

`make verify` retains its formatting, lint, runtime-integrity, Python, and Chromium checks.
`make validation` remains the focused scientific regression command; required CI job names stay
unchanged.

`make e2e` produces `.build/e2e/results.xml`, per-test Playwright traces, and screenshots on both
successful and failed runs. Traces record browser actions, snapshots, and network activity; the
JUnit report records individual results. Reproduce the checks with `uv sync --locked`, the matching
Chromium installation, and `make e2e`. Only synthetic test inputs appear in these ignored artifacts.
Python-only runs leave them intact; the next E2E run replaces them.

## Test-server reliability

Delivery verification on 2026-10-13 reproduced connection resets during parallel Python-asset
loads from the local test server. A synthetic burst check failed 90 of 125 requests with the
default listen backlog of 5 and none with 128. The browser fixture uses a backlog of 128 while
retaining the same local binding, static assets, and real worker. Application code is unchanged.
