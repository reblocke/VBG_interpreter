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

- observed and algebraically completed current VBG values;
- an optional modeled arterial pH–PaCO₂ sensitivity region;
- current serum-chemistry context; and
- one optional prior observation as longitudinal context.

Absence or refusal of one lane must not erase valid information from another lane.

Any two of current pH, PvCO₂, and blood-gas HCO₃ are sufficient for venous-gas completion. The
result identifies which coordinates were supplied and which were derived. Its venous pH reference
orientation is descriptive only; it is not a Boston ruleset classification applied directly to a
VBG.

## Candidate arterial region

The generic candidate region uses a published-agreement sensitivity scenario for pH and PaCO₂
after any two-of-three venous-gas completion. It is not an individual correction, prediction
interval, arterial measurement, or claim of VBG–ABG interchangeability. The generic pH component
is retained for every available candidate region. The generic PaCO₂ component is replaced only by
the narrowly gated Farkas/Jörg **PaCO₂ component**, never by a Farkas pH component.

Known central, mixed, or capillary specimen types; known central or pulmonary-artery catheter
draw sites; or `YES` for poor perfusion/hemodynamic instability, recent major ventilation/treatment
change, or material preanalytic concern suppress the arterial sensitivity region. These fields
deliberately have no newly invented blood-pressure, lactate, tourniquet, delay, or treatment-time
threshold.

Unknown specimen, draw site, or the three clinical-condition fields is not favorable context. It
does not enable the gated PaCO₂ upgrade, but it may leave the generic scenario available with
explicit warnings and an unknown-applicability limitation. A nonpositive or nonfinite generic
endpoint is a model-domain refusal; the Explorer does not clamp an endpoint because that could
shrink the sensitivity region and create a false exclusion.

The PaCO₂ upgrade requires all of the following: same-sample venous oxygen saturation with an
explicit unit, peripheral venous specimen type, upper-extremity peripheral draw site, and `NO` for
each of poor perfusion/hemodynamic instability, recent major ventilation/treatment change, and
material preanalytic concern. Supplemental oxygen can be `YES`, `NO`, or `UNKNOWN`; it selects the
recorded PaCO₂ profile and is not an oxygenation calculation. If the PaCO₂ axis was
Henderson–Hasselbalch derived, it does not receive the external-evaluation label.

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

Every current chemistry field is optional. Serum total CO₂ is serum chemistry, not blood-gas HCO₃.
The Explorer does not invert it into current PaCO₂ or use it to hard-filter the candidate arterial
state set. It calculates serum anion gap only when sodium, chloride, and serum total CO₂ are all
supplied, and optional albumin-corrected context only when albumin is also supplied. A full Stewart
partition requires supplied venous pH, venous base excess, albumin, sodium/chloride, and
same-clinical-timepoint chemistry; it is labelled `VENOUS_BASIS` and does not infer arterial SBE.

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

Version `0.2.0` is the current public research preview, deployed from the same reviewed `main`
commit identified by its release manifest. The historic `v0.1.0` preview and the current preview
establish reproducible implementations and documented software contracts only; neither establishes
clinical accuracy, safety, utility, generalizability, diagnostic performance, patient benefit,
regulatory status, or management equivalence. Any future clinical evaluation requires a separately
governed study and must not be inferred from the synthetic verification suite.
