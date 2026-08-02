# Clinical scope

## Purpose and limit

VBG Acid–Base Explorer is exploratory research/educational software. It presents measurements,
deterministic calculations, and explicitly bounded modeled possibilities. It is not clinically
validated, not a medical device, and does not provide diagnosis, treatment direction, or a basis
to substitute a VBG for an ABG when an arterial measurement is clinically required.

Public availability, an open-source license, passing software tests, and a hosted demonstration do
not change this scope. The intended users are educators, researchers, and software reviewers using
synthetic inputs. It is not intended for bedside decision
support, triage, monitoring, screening, diagnostic exclusion, or autonomous interpretation.

## Input lanes

The Explorer keeps four lanes separate:

- observed current VBG values;
- an optional modeled arterial pH–PaCO₂ sensitivity region;
- current serum-chemistry context; and
- one optional prior observation as longitudinal context.

Absence or refusal of one lane must not erase valid information from another lane.

## Candidate arterial region

The initial modeled region is available only when all of the following are explicit:

- same-sample venous oxygen saturation with an explicit unit;
- peripheral venous specimen type;
- upper-extremity peripheral draw site;
- no known poor perfusion or hemodynamic instability;
- no recent major ventilation or treatment change; and
- no material preanalytic concern.

For the three clinical-condition fields, `YES` blocks the modeled region and `UNKNOWN` is
insufficient context. `NO` is required. These fields deliberately have no newly invented blood
pressure, lactate, tourniquet, delay, or treatment-time threshold. Supplemental oxygen can be
`YES`, `NO`, or `UNKNOWN`; it selects the recorded conservative PaCO₂ uncertainty profile and is
not an oxygenation calculation.

An unavailable candidate region is not a claim that the observed VBG or chemistry is invalid. It
only withholds model-dependent arterial conclusions.

## Set-valued output

When a candidate region is available, the Explorer evaluates both named chronicity branches and
uses certified terminal-path feasibility to enumerate every compatible state of the retained
software ruleset. It never chooses a headline diagnosis from a point estimate or from the number
of rendered visual samples.

Conclusions use only the predicates defined in
[the interpretation specification](INTERPRETATION_SPEC.md). “Excluded” always means excluded
within the stated modeled state space; it never means globally excluded for the person.

## Chemistry and prior observations

Serum total CO₂ is serum chemistry, not blood-gas HCO₃. The Explorer does not invert it into
current PaCO₂ or use it to hard-filter the candidate arterial state set. It calculates serum anion
gap and optional albumin-corrected context. A full Stewart partition requires supplied venous base
excess, albumin, and same-clinical-timepoint chemistry; it is labelled `VENOUS_BASIS` and does not
infer arterial SBE.

A prior ABG may be displayed as historical arterial context. A prior VBG remains venous, and a
prior serum total-CO₂ value remains chemistry. One prior observation cannot prove chronicity,
exclude acute-on-chronic disease, or automatically narrow the current model.

## Prohibited inferences

The Explorer does not estimate or infer PaO₂, arterial oxygen saturation, A–a gradient, P/F ratio,
tissue hypoxia, oxygen extraction, arterial SBE, analyzer equivalence, VBG–ABG interchangeability,
or management equivalence.

## Privacy

The browser is static and client-side. It does not persist entered values to a URL, browser
storage, telemetry service, calculation backend, or export. GitHub Pages still receives ordinary
same-origin page and asset requests; application code does not place entered values in those
requests. Users must not enter PHI or real patient data.

## Release claim boundary

Version `0.1.0` is a public research preview. It establishes a reproducible implementation and
documented software contract only. It does not establish clinical accuracy, safety, utility,
generalizability, diagnostic performance, patient benefit, regulatory status, or management
equivalence. Any future clinical evaluation requires a separately governed study and must not be
inferred from the synthetic verification suite.
