# Architecture

The v0.3 Explorer is one static research/educational app with one public Python interpretation
entry point, `vbg_interpreter.interpret_vbg`. Python determines capability availability;
JavaScript validates input shape and renders the result without repeating scientific inference.

## Data flow

A strict `vbg_explorer_request/3.0` contains current VBG values, optional current chemistry, and
tri-state context. At least one VBG value is required. Each dependent calculation handles missing
operands, known scope exclusions, and numerical-domain refusal locally. Results use
`vbg_explorer_result/3.0` and retain supplied, HH-derived, calculated SBE, and modeled origins.

- `models.py` defines compact input/result contracts. `mapping.py` preserves the strict JSON
  boundary, including decimal strings, exact keys, explicit units, and duplicate rejection.
- `venous_gas.py` echoes source measurements, completes missing gas coordinates using HH, and
  selects reported standard base excess or calculates venous-basis SBE with the approved
  normothermic Van Slyke equation.
- `arterial_paco2.py` reads only source PvCO2 and same-sample saturation. It cannot receive
  completed-gas coordinates. Applicability is separate from availability and evidence tier.
- `chemistry.py` computes serum AG, corrected AG, Na−Cl, and the optional venous Stewart partition.
- `screening.py` returns `NOT_CONFIGURED`; no categorical threshold is installed.
- `information.py` ranks at most three next-input descriptions with a deterministic interface
  heuristic, not a claim of measured diagnostic information gain.
- `interpret.py` composes the capabilities without a global gas-completion prerequisite.

The pinned `stewartlight@f277cac54801d85366cbadbf11804f6643f6a869` structured helper owns Stewart
partition formulas. It accepts pH, SBE, Na, Cl, albumin, and optional lactate. The Explorer supplies
measured venous pH and reported or explicitly calculated venous SBE; serum total CO2 is never an
operand. The helper documents supplied SBE; the Explorer's calculated-SBE adaptation is a
separate documented derivation, not new upstream or clinical validation.

## Static browser build

`scripts/build_web.py` replaces ignored `.build/web/`, copying `web/` and staging the installed
Explorer and pinned upstream Python package. It creates a deterministic package manifest and
release manifest. No generated package copy is committed. The self-hosted Pyodide worker loads
only same-origin assets and invokes the single JSON browser adapter.

The form has VBG, optional chemistry, and collapsed model-context sections. Five top-level result
cards separate venous facts, chemistry, the optional PaCO2 estimate, uncertainty, and collapsed
methods/evidence. Editing or resetting invalidates pending worker responses before rendering.
Safe DOM text rendering, labeled controls, keyboard access, and responsive layout are required.

## Privacy and publication

There is no backend, entered-value logging, storage, URL state, telemetry, or export. Ordinary
same-origin hosting requests load the code/runtime. No patient inputs are used in testing.

Public `reblocke/VBG_interpreter` main is canonical. The historical private repository has an
intentionally unrelated history and remains private and archived. Do not merge private ancestry
into public main. Pages verifies public visibility, required checks, the exact source commit,
and the current main identity; the release manifest records the same reviewed source commit.

`make verify` checks formatting, lint, Pyodide integrity, Python contracts, staging, and Chromium
E2E. `make validation` runs the synthetic scientific capability matrix. Neither is clinical
validation. Required CI job names remain `verify` and `validation`.
