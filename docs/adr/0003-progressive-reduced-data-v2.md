# ADR 0003: Progressive reduced-data VBG interpretation

## Status

Accepted 2026-08-04. This design decision was subsequently authorized for source and Pages
publication under the v0.2.0 supplement in `docs/PUBLIC_RELEASE_REVIEW.md`.

## Context

The v1 workflow made pH, PvCO₂, sodium, chloride, and serum total CO₂ mandatory before it could
return an assessment. That needlessly discarded an interpretable venous-gas pair and coupled the
arterial sensitivity lane to optional chemistry. It also treated the saturation-based Farkas
model as an all-or-nothing pH–PaCO₂ model, even though its retained external evaluation concerns
only PaCO₂.

The product must preserve a conservative research boundary: a missing field may withhold only the
claim that depends on it; a generic population result must not be presented as individual
arterial conversion; and any possible/excluded result must continue to come from the certified
state-space engine rather than a display grid or point estimate.

## Decision

### Progressive inputs and venous origins

The v2 request accepts any two of pH, PvCO₂, and blood-gas HCO₃. Henderson–Hasselbalch completes
the third coordinate and serializes an origin for every axis. When all three are supplied, the
Explorer retains them and reports a pH/PvCO₂ HCO₃ comparator/discrepancy instead of overwriting a
value. Serum total CO₂ remains a separate serum-chemistry input and is never used to complete a
venous gas or infer current PvCO₂.

The completed coordinate is still venous. The pH display can state only whether the venous pH is
below, within, or above a retained reference band; it cannot run the Boston ruleset directly on
the VBG.

### Generic component-selected sensitivity region

When no known model blocker is present, use the signed Bloom 2014 venous-minus-arterial (`V − A`)
average difference as a best-guess orientation and retain the documented study-level extrema as a
source-derived sensitivity scenario:

| Axis | Retained `V − A` mean | Retained `V − A` extrema | Arterial point orientation | Arterial scenario endpoints |
| --- | ---: | ---: | --- | --- |
| pH | `−0.033` | `−0.18`, `+0.10` | `pHv + 0.033` | `pHv − 0.10`, `pHv + 0.18` |
| PaCO₂ (mmHg) | `+4.41` | `−20.4`, `+26.0` | `PvCO₂ − 4.41` | `PvCO₂ − 26.0`, `PvCO₂ + 20.4` |

The values are sign-converted into arterial coordinates because the source convention is venous
minus arterial. The generic pH component is used for every available candidate. The generic
PaCO₂ component is used unless its narrowly defined upgrade gates pass.

This rectangle is named the **published study-level agreement-extrema scenario envelope**. It is
not a 95% interval, confidence interval, prediction interval, probability, likelihood, or an
individual correction. Its pH and PaCO₂ margins are marginal source summaries, not a jointly
validated distribution; treating their Cartesian product as joint coverage is prohibited.

The generic components are `DERIVATION_ONLY`. A pH or PvCO₂ coordinate reconstructed from the
other two venous-gas inputs remains outside the population-model evaluation and must retain that
limitation.

### PaCO₂-only Farkas/Jörg upgrade

Use the Farkas/Jörg PaCO₂ component only when all gates are explicit: peripheral venous specimen,
upper-extremity peripheral draw site, same-sample venous saturation with an explicit unit, and
`NO` for poor perfusion/hemodynamic instability, recent major ventilation/treatment change, and
material preanalytic concern. The upgrade changes only PaCO₂. It does not replace generic pH.

The external-evaluation label applies only to a supplied PvCO₂ in that eligible setting. A
Henderson–Hasselbalch-derived PvCO₂ does not inherit it. Unknown context never satisfies an
upgrade gate; it can leave the generic scenario available only with warnings and an
unknown-applicability limitation.

Known central, mixed, or capillary specimens; central or pulmonary-artery catheter draws; and a
known `YES` for any of the three limiting contexts suppress model-dependent arterial conclusions.
If a generic endpoint is nonpositive or nonfinite, the model refuses the domain rather than
clamping the endpoint. Clamping would reduce the candidate region and could manufacture a false
exclusion. A refusal retains the attempted components' model, profile, and evidence identities but
does not publish the invalid point or intervals.

### Progressive chemistry

Every chemistry input is optional. Sodium, chloride, and serum total CO₂ together support serum
anion gap; albumin additionally supports albumin-corrected context; the Stewart partition has its
separate venous-pH/base-excess/chemistry/time requirements. Omission of any chemistry field must
not remove the completed venous-gas, candidate-region, or state-space lanes.

## Consequences

- The browser can return a caveated assessment with only a valid two-of-three venous-gas pair.
- The result makes raw/derived origins, model component choices, warnings, and non-evaluable
  chemistry explicit rather than silently assuming favorable data.
- Possible and excluded language remains limited to the certified state space inside the declared
  sensitivity scenario, never to the person globally.
- The change adds no patient data, backend, telemetry, URL state, browser storage, export, or
  patient-derived example.
- The stronger reduced-data workflow does not establish clinical validation, medical-device status,
  diagnosis, treatment guidance, or ABG replacement.

## Source and reuse boundary

Bloom BM, Grundlingh J, Bestwick JP, Harris T. The role of venous blood gas in the Emergency
Department: a systematic review and meta-analysis. *European Journal of Emergency Medicine.*
2014;21(2):81–88. [doi:10.1097/MEJ.0b013e32836437cf](https://doi.org/10.1097/MEJ.0b013e32836437cf).
The bibliographic record and retained numerical constants were reviewed 2026-08-04. This ADR
records independently expressed numeric implementation choices; it does not reproduce the article
or distribute its full text, tables, figures, or layout. See [EVIDENCE.md](../EVIDENCE.md) and
[THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md) for the product evidence and attribution
boundaries.
