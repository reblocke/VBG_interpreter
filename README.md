# VBG Acid–Base Explorer

VBG Acid–Base Explorer is an open-source research and educational application for exploring what
can—and cannot—be concluded from a current venous blood gas (VBG), current BMP/CMP chemistry,
limited clinical context, and at most one prior observation.

**[Open the hosted v0.2 research preview](https://reblocke.github.io/VBG_interpreter/)**

The Explorer is deliberately set-valued. It keeps measured, calculated, modeled, and historical
information separate and reports:

- features present across every modeled arterial state;
- features possible in some modeled states;
- features excluded only within the explicitly modeled state space; and
- questions that are not evaluable from the supplied information.

It is not clinically validated, is not a medical device or medical advice, and must not be used
to diagnose, treat, or replace an arterial blood gas (ABG) when arterial confirmation is required.
Use synthetic values only; do not enter PHI or real patient data.

## Intended use cases

The Explorer is designed for:

- teaching how venous measurements, serum chemistry, and modeled arterial possibilities differ;
- examining how uncertainty changes a software-ruleset acid–base classification;
- testing synthetic scenarios and research hypotheses;
- reviewing the provenance and limitations of the implemented calculations; and
- developing or auditing set-valued scientific-software methods.

It is not intended for:

- patient-specific diagnosis, treatment, triage, monitoring, or management;
- deciding that an ABG is unnecessary;
- inferring PaO₂, arterial saturation, A–a gradient, P/F ratio, tissue hypoxia, oxygen extraction,
  or arterial standard/base excess;
- treating serum total CO₂ as blood-gas HCO₃ or inverting chemistry to estimate current PaCO₂;
- claiming analyzer equivalence, VBG–ABG interchangeability, or a patient-specific probability;
  or
- claims of readiness or suitability for commercial, operational, or regulated clinical
  deployment.

## What it accepts

The single workflow has four input lanes:

1. **Current VBG:** any two of pH, PvCO₂, and blood-gas HCO₃ are required. The Explorer labels
   the supplied coordinates and completes the third only with the documented
   Henderson–Hasselbalch relation. Venous base excess, same-sample venous saturation with an
   explicit unit, specimen type, and draw site are individually optional.
2. **Current BMP/CMP:** every chemistry field is optional. Sodium, chloride, and serum total CO₂
   together allow a serum anion gap; albumin adds the documented correction when that gap is
   available; lactate and the chemistry-to-VBG time relationship remain separate context.
3. **Optional context:** explicit tri-state poor-perfusion/hemodynamic, recent major
   ventilation/treatment-change, preanalytic, and supplemental-oxygen fields.
4. **One optional prior observation:** ABG, VBG, or serum total CO₂, retained as historical context
   rather than proof of chronicity.

Missing values limit only dependent output. The minimum gas pair can still support a completed
venous-gas display, caveated candidate sensitivity region, and certified state-space assessment
when its model domain is valid. Missing chemistry withholds only chemistry-dependent calculations.
Known out-of-scope specimen/context conditions suppress arterial-model conclusions; unknown model
context remains an explicit caveat and never silently becomes favorable context.

## What it returns

The Explorer first shows a completed **venous** pH–PvCO₂–blood-gas-HCO₃ coordinate, including
which values were supplied or Henderson–Hasselbalch derived. Its venous pH orientation is
descriptive only; it is not a Boston interpretation applied directly to venous values.

Absent a known model blocker and within the model domain, it then calculates a deterministic
pH–PaCO₂ sensitivity rectangle and exhaustively enumerates the compatible states of the retained
Boston-style software ruleset. The pH component uses the generic published-agreement scenario
model. The PaCO₂ component uses that generic model unless all documented peripheral,
same-sample-saturation, and context gates allow the Farkas/Jörg PaCO₂-only upgrade. The coordinate
display is explanatory only: its colors, areas, samples, and cell counts have no probability,
prevalence, likelihood, confidence, or frequency meaning. A modeled point is orientation, not “the
arterial result.”

Chemistry is evaluated field by field in parallel. Serum anion gap is available only from supplied
sodium, chloride, and serum total CO₂; albumin-dependent context and the venous-basis Stewart
partition appear only when their required inputs are present. A prior observation remains in its
original specimen/provenance lane and does not prune acute or chronic branches.

The live schemas are:

- `vbg_explorer_request/2.0`
- `vbg_explorer_result/2.0`

See the [interpretation specification](docs/INTERPRETATION_SPEC.md) for the exact set predicates
and [clinical scope](docs/CLINICAL_SCOPE.md) for applicability and non-use boundaries.

## Scientific caveats

- The generic pH and PaCO₂ components are source-derived sensitivity scenarios, not individual
  VBG-to-ABG conversions. Their source extrema are neither prediction intervals nor joint pH–PaCO₂
  coverage claims.
- The Farkas/Jörg external-evaluation label applies only to the eligible, supplied-PvCO₂ PaCO₂
  component. It does not validate generic pH, a Henderson–Hasselbalch-derived axis, or the combined
  Explorer.
- A completed venous coordinate and its descriptive pH orientation remain venous. Calculated HCO₃
  is a derived blood-gas value, not a measured arterial bicarbonate or serum total CO₂.
- The Boston-style engine is compatibility software behavior, not an adjudicated clinical
  standard or a validated diagnostic target.
- The source population and applicability spectrum are incompletely characterized.
- A prior gas or chemistry value can add context but cannot prove chronicity or exclude an
  acute-on-chronic process.
- Public source availability and code verification do not create clinical evidence.

Read the complete [evidence and provenance record](docs/EVIDENCE.md) and
[third-party notices](THIRD_PARTY_NOTICES.md) before reusing calculations or claims.

## Privacy and hosting

The static app performs calculations locally in the browser. Application code does not place
entered values in the URL, browser storage, telemetry, a calculation backend, or an export. Page
loading still makes ordinary same-origin HTTPS requests to GitHub Pages, whose infrastructure may
retain standard request/security logs; entered form values are not included in those requests.
Do not enter PHI, credentials, restricted data, or real patient values.

## Local development

Prerequisites are Python 3.11+, [`uv`](https://docs.astral.sh/uv/), and Chromium for browser tests.

```bash
uv sync --locked
uv run playwright install chromium
make test
make validation
make e2e
make verify
make serve
```

`make serve` generates an ignored `.build/web/` bundle, stages the installed `vbg_interpreter`
package and pinned upstream `stewartlight` dependency, and serves the site at
`http://127.0.0.1:8000`. No generated Python copy is committed.

The public Python entry point is `vbg_interpreter.interpret_vbg(request)`. Construct typed inputs
from `vbg_interpreter.models`, or use `request_from_mapping()` at a strict JSON boundary. All
examples and tests in this repository use synthetic values.

## Architecture and dependency boundary

This repository is not a second ABG application. It uses the structured calculation helper from
[`reblocke/stewart-light`](https://github.com/reblocke/stewart-light) pinned at commit
`f277cac54801d85366cbadbf11804f6643f6a869`. The upstream ABG educational app is available at
[Stewart Light](https://reblocke.github.io/stewart-light/).

See [architecture](docs/ARCHITECTURE.md), [contributor guidance](CONTRIBUTING.md),
[community conduct](CODE_OF_CONDUCT.md), and [security/privacy reporting](SECURITY.md). Pull
requests must keep the `verify` and `validation` checks green and use synthetic data only.

## Reports and support

Use the [research-software issue form](https://github.com/reblocke/VBG_interpreter/issues/new/choose)
for reproducible non-sensitive reports using synthetic values. Use
[private vulnerability reporting](https://github.com/reblocke/VBG_interpreter/security/advisories/new)
for suspected security or privacy vulnerabilities. This project does not provide clinical advice,
patient-specific interpretation, or emergency support.

## Version, citation, and license

Version `0.2.0` is the current public research preview. The hosted Explorer is deployed only from
the reviewed `main` commit and publishes that exact source identity in `release-manifest.json`.
Cite the manifest commit or the exact source commit used. Structured citation metadata are in
[CITATION.cff](CITATION.cff). Repository-authored code is available under the [MIT License](LICENSE),
subject to the separate attributions and boundaries in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

The research/educational intended-use boundary describes the product's evidence and safety claims;
it does not add a restriction to the MIT license for repository-authored code. Third-party
components remain governed by their recorded licenses and notices.

The simplification and publication of this codebase do not create new clinical evidence.
