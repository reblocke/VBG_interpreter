# Evidence and provenance

## Purpose

This is the evidence boundary for the live v2 Explorer contract. It records what the software
computes and what each component does *not* establish. It is not an end-to-end clinical-validation
packet, a claim of VBG–ABG interchangeability, or an individual arterial conversion method.

The implementation is public for inspection and reproducibility. Passing synthetic tests,
publication of source code, and a cited source do not raise an evidence tier or establish clinical
accuracy.

## Component evidence map

| Output | Method identity | Evidence status | Principal source | Binding limitation |
| --- | --- | --- | --- | --- |
| Supplied current VBG coordinate | Observed input | Measured/reported venous | User-supplied synthetic input | Remains venous |
| Completed venous pH/PvCO₂/HCO₃ | Henderson–Hasselbalch (`0.0307`, `6.095`) | `DERIVED_CALCULATION` for a completed axis | Documented constants | Algebraic completion, not arterialization |
| Venous pH orientation | Reference-band comparison | Descriptive only | Implemented display rule | Not a Boston interpretation of VBG values |
| Generic candidate pH | `generic_peripheral_vbg_offset_v1` | `DERIVATION_ONLY` | Bloom et al. 2014 | Scenario envelope, not an individual conversion |
| Generic candidate PaCO₂ | `generic_peripheral_vbg_offset_v1` | `DERIVATION_ONLY` | Bloom et al. 2014 | Scenario envelope, not an individual conversion |
| Eligible PaCO₂-only upgrade | `farkas_simplified_93_v1` plus Jörg profile | `EXTERNALLY_EVALUATED` only for supplied PvCO₂ | Jörg et al. 2023 | Does not validate pH, a derived PvCO₂ axis, or the full Explorer |
| Candidate state set | `stewartlight_boston_ruleset_v1` | `IMPLEMENTED_SOFTWARE_RULESET` | Repository compatibility behavior | Not an adjudicated clinical standard |
| Serum anion gap | Na − Cl − serum total CO₂ | `DERIVED_CALCULATION` | Documented repository formula | Serum chemistry only |
| Optional Stewart partition | Pinned structured upstream helper | `IMPLEMENTED_SOFTWARE_RULESET` | `stewartlight@f277cac` | Venous basis; requires supplied pH, base excess, and same-time chemistry |

## Progressive venous-gas completion

The only minimum current-gas requirement is any two of pH, PvCO₂, and blood-gas HCO₃. The
Explorer completes the third coordinate with the retained Henderson–Hasselbalch relation and
labels each coordinate `SUPPLIED` or `DERIVED_HENDERSON_HASSELBALCH`. This is algebraic completion
of a **venous** gas, not a conversion to an arterial measurement.

When all three values are supplied, none is silently replaced. The result retains the supplied
HCO₃, calculates a pH/PvCO₂ comparator, and reports a typed discrepancy limitation when the
absolute difference exceeds the documented 0.5 mmol/L display threshold. Serum total CO₂ is never
substituted for blood-gas HCO₃, and chemistry is never inverted to create current PvCO₂.

If pH or PvCO₂ is Henderson–Hasselbalch derived, that axis remains outside the population-model
evaluation used for the candidate region. It retains a derivation-only evidence label even when
the supplied inputs otherwise meet a PaCO₂-upgrade gate.

## Component-selected candidate arterial sensitivity region

### Generic component

For each available candidate region, the pH component is the generic Bloom-derived component. The
implementation uses the reported venous-minus-arterial (`V − A`) mean and retained
study-level agreement extrema from Bloom et al. 2014, then converts their sign into arterial
coordinates:

| Axis | Point orientation | Published study-level agreement-extrema scenario envelope |
| --- | --- | --- |
| pH | `pHv + 0.033` | `pHv − 0.10` through `pHv + 0.18` |
| PaCO₂ (mmHg) | `PvCO₂ − 4.41` | `PvCO₂ − 26.0` through `PvCO₂ + 20.4` |

The source values retained by the implementation are pH `V − A` mean `−0.033` with extrema
`−0.18` and `+0.10`, and PaCO₂ `V − A` mean `+4.41 mmHg` with extrema `−20.4` and `+26.0 mmHg`.
The conversion above explains why the arithmetic signs reverse for arterial coordinates. The
implementation does not reproduce the source table, figure, or article text.

The generic pH and PaCO₂ envelopes are a deterministic **published study-level agreement-extrema
scenario envelope**. They are not a 95% interval, confidence interval, prediction interval,
probability, frequency, likelihood, or patient-specific coverage claim. The pH and PaCO₂ margins
are separately sourced and form a Cartesian rectangle; their joint coverage was not established.
Both generic components are `DERIVATION_ONLY` and have no individual external-validation claim.

Known central, mixed, or capillary specimen types; known central or pulmonary-artery catheter draw
sites; and explicit `YES` poor-perfusion/hemodynamic, recent major ventilation/treatment-change,
or material-preanalytic concern suppress the arterial sensitivity region. Unknown specimen, draw
site, or context does not establish favorable applicability: the generic component can still run
only with explicit warnings and an unknown-source-applicability limitation. A nonpositive or
nonfinite candidate endpoint is a typed model-domain refusal. The code does not clamp a PaCO₂
endpoint to a positive value, because doing so could shrink the scenario envelope and create a
false exclusion.

### PaCO₂-only Farkas/Jörg upgrade

The generic PaCO₂ component is replaced only when all of the following are explicit: peripheral
venous specimen type, upper-extremity peripheral draw site, same-sample venous saturation with an
explicit unit, and `NO` for poor perfusion/hemodynamic instability, recent major
ventilation/treatment change, and material preanalytic concern. In that narrow setting, the
Explorer applies the retained Farkas saturation equation to **PaCO₂ only** and uses the
oxygen-context Jörg profile for the PaCO₂ sensitivity range.

The Farkas/Jörg component carries `EXTERNALLY_EVALUATED` evidence only when PvCO₂ was supplied.
If PvCO₂ was reconstructed from pH and blood-gas HCO₃, it remains derivation-only and gets an
explicit outside-population-model-evaluation limitation. Its descriptor still preserves the
Farkas, Jörg, and Henderson–Hasselbalch source identifiers used for that component; it does not
substitute generic Bloom provenance or claim external validation. The upgrade never replaces the
generic pH component, never converts a venous result into an arterial measurement, and does not
validate the combined pH–PaCO₂ rectangle, the state labels, or any individual patient estimate.

Jörg et al. 2023 documents the retained PaCO₂ formula and component evaluation
([doi:10.1186/s40635-023-00564-w](https://doi.org/10.1186/s40635-023-00564-w)). Bloom et al. is
cited below for the generic component. Neither source is treated as a clinical validation of the
Explorer.

## Candidate state rules and certified conclusions

The retained Boston compatibility engine is identified as `stewartlight_boston_ruleset_v1`. It is
an `IMPLEMENTED_SOFTWARE_RULESET`, not an adjudicated clinical gold standard. The Explorer uses a
certified terminal-path feasibility implementation over the candidate rectangle rather than a
finite display grid to derive possible states. It evaluates both chronicity branches by design.

Certification establishes feasibility only within the submitted model rectangle and retained
ruleset. It cannot create coverage, calibration, diagnosis, treatment, or global exclusion claims.
The displayed coordinate samples are explanatory only and never drive possible/excluded output.

## Progressive serum chemistry and Stewart context

Every current-chemistry field is optional. An empty chemistry lane is `NOT_PROVIDED`; a partially
supplied lane is `PARTIAL`; and a lane with sodium, chloride, and serum total CO₂ can calculate a
serum anion gap. Albumin adds an albumin-corrected anion-gap context only when both the anion gap
and albumin are present. Lactate remains a separately supplied chemistry value.

The optional `VENOUS_BASIS` Stewart partition requires supplied VBG pH, measured venous base
excess, supplied sodium/chloride/albumin, and a same-clinical-timepoint relationship. It does not
use a Henderson–Hasselbalch-derived pH, infer arterial SBE, or accept PvCO₂, blood-gas HCO₃, or
serum total CO₂ as a partition operand.

## Source identifiers and restrictions

The local evidence descriptors preserve source identifiers including `bloom_2014`,
`farkas_2012_public_manuscript`, `jorg_2023`, `krbec_2022`, and
`clsi_c46_a2_official_record`. These identifiers document the current evidence boundary; they do
not transfer rights or authorize copying restricted text, figures, tables, standards, or
unpublished material. See [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

Bloom BM, Grundlingh J, Bestwick JP, Harris T. The role of venous blood gas in the Emergency
Department: a systematic review and meta-analysis. *European Journal of Emergency Medicine.*
2014;21(2):81–88. [doi:10.1097/MEJ.0b013e32836437cf](https://doi.org/10.1097/MEJ.0b013e32836437cf).
The bibliographic record and the retained numeric constants were reviewed 2026-08-04. No source
artifact, full text, table, figure, or layout is distributed in this repository.

## Verification versus validation

The deterministic synthetic matrix checks progressive input completion, supplied-versus-derived
origins, signed scenario arithmetic, no-clamp domain refusals, partial chemistry, certified
set-predicate semantics, and browser contracts. It does not estimate clinical bias, limits of
agreement, coverage, sensitivity, specificity, calibration, subgroup performance, or patient
outcomes. No protected or patient-derived validation dataset is included or executed in this
repository. Those questions remain future external scientific work.
