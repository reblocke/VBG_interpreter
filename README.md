# VBG Acid–Base Explorer

Enter the VBG and chemistry values you have. The Explorer reports only the measurements,
calculations, screening statements, and model estimates supported by those inputs. Missing values
suppress only the dependent result. Categorical screening is not configured in v0.4.

**[Open the hosted v0.4 research preview](https://reblocke.github.io/VBG_interpreter/)**

This client-side app is for research and education. It is not clinically validated, is not medical
advice, and must not be used to diagnose, treat, or replace an ABG when arterial confirmation is
required. Use synthetic values only; do not enter PHI or real patient data.

## Intended use cases

- Inspect measured venous values, direct calculations, and their provenance.
- Explore how available inputs enable individual calculations without filling missing data.
- Review the assumptions and limitations of a separately labeled arterial PaCO2 estimate.
- Test reproducible synthetic scenarios and audit scientific software behavior.

### It is not intended for

Patient-specific diagnosis, treatment, triage, monitoring, arterial oxygenation inference,
management decisions, claims of analyzer equivalence, or deciding that an ABG is unnecessary.

## What it accepts

One or more VBG values: pH, PvCO2 with unit, blood-gas HCO3 with reported/calculated/unknown basis,
reported base excess with standard/actual/unknown basis, or unit-explicit venous O2 saturation.
Every CMP/BMP field is optional: sodium, chloride, serum total CO2, albumin, and lactate.
Saturation is labeled as same-sample venous O2 saturation, not SpO2 or PO2. There is no clinical-context questionnaire. Chemistry timing refines only the venous Stewart calculation.

## What it returns

| Available inputs | Supported result |
| --- | --- |
| Any one VBG value | Reported venous fact with units and provenance |
| Any two core gas coordinates | HH completion of the third, explicitly derived |
| All three coordinates | Neutral reported-minus-HH HCO3 difference |
| Reported standard BE, or sufficient gas coordinates | Reported or calculated venous SBE; calculated values assume 37°C |
| Measured venous pH and/or PvCO2 | Rough arterial estimates: pH + 0.04 and PvCO2 − 5 mmHg |
| Measured PvCO2 and same-sample venous saturation | Farkas replaces the fixed CO2 correction; conservative population agreement range |
| Both measured pH and PvCO2 | Modeled arterial bicarbonate and a provisional Boston interpretation; BE not required |
| Na, Cl, serum total CO2 | Serum anion gap |
| AG operands and albumin | Albumin-corrected AG, without a universal reference cutoff |
| Na and Cl | Descriptive Na−Cl difference |
| Measured venous pH, reported/calculated SBE, same-time Na/Cl/albumin | Venous Stewart partition; optional lactate component |

Derived pH/PvCO2 remain venous and cannot act as independently measured model inputs. Reported
actual or unspecified BE is not relabeled as SBE. If reported standard BE is absent, calculated
SBE uses the selected Van Slyke equation and carries its derivation and normothermia assumption
into any eligible partition. Serum total CO2 is never substituted for blood-gas HCO3.

“What’s known” separates supplied measurements from venous/chemistry calculations. “Best guess”
shows estimated arterial values and an explicitly provisional acid–base interpretation. Matching
pH × CO2 plots display measured and estimated coordinates with shared scales. Their reference
cross (pH 7.40 / CO2 40 mmHg) is descriptive, not a validated venous cutoff. The plots never infer
or exclude a disorder. Single coordinates retain partial output without inventing a plotted pair.

Fixed corrections are owner-selected heuristics, without individual uncertainty bounds. Farkas
changes only PaCO2; pH retains +0.04. All applicability is unassessed. Its conservative agreement
range is not individual confidence or a joint pH/CO2 region. The combined provisional assessment
has not been clinically validated and does not establish chronicity. BE is optional throughout.

The bottom formulas/evidence box remains expandable; general research/privacy wording appears
once in the footer. Numerical failure preserves independent results.

The live schemas are `vbg_explorer_request/4.0` and `vbg_explorer_result/4.0`, without compatibility
shims. See the [interpretation specification and synthetic examples](docs/INTERPRETATION_SPEC.md),
[clinical scope](docs/CLINICAL_SCOPE.md), and [evidence record](docs/EVIDENCE.md).

## Scientific caveats

The 7.35–7.45 pH comparison is descriptive, not a validated venous normal interval. No categorical
PvCO2 screening cutoff is configured. The Farkas/Jörg component has external-evaluation evidence,
but its range is not a patient-specific probability interval. Calculated venous SBE does not
establish arterial SBE or analyzer equivalence. There is no validated local end-to-end VBG
algorithm. Screening, prediction, compensation classification, and management equivalence are
separate claims. Public availability and passing software tests create no new clinical evidence.

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

Version `0.4.0` is the current public research preview. The hosted Explorer is deployed only from
the reviewed `main` commit and publishes that exact source identity in `release-manifest.json`.
Cite the manifest commit or the exact source commit used. Structured citation metadata are in
[CITATION.cff](CITATION.cff). Repository-authored code is available under the [MIT License](LICENSE),
subject to the separate attributions and boundaries in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

The research/educational intended-use boundary describes the product's evidence and safety claims;
it does not add a restriction to the MIT license for repository-authored code. Third-party
components remain governed by their recorded licenses and notices.

The simplification and publication of this codebase do not create new clinical evidence.
