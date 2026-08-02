# Evidence and provenance

## Purpose

This is a compact evidence boundary for the live Explorer. It records what the software computes
and what each component does *not* establish. It is not an end-to-end clinical validation packet.

The implementation is public for inspection and reproducibility. Publication, owner rights
attestation, and passing synthetic tests do not raise any evidence tier.

## Component evidence map

| Output | Method identity | Evidence status | Principal source | Binding limitation |
| --- | --- | --- | --- | --- |
| Current VBG values | Observed input | Measured/reported venous | User-supplied synthetic input | Remains venous |
| Modeled arterial pH | `farkas_simplified_93_v1` | `DERIVATION_ONLY` | Farkas 2012 redacted derivation | No external pH validation; deterministic range is not a probability interval |
| Modeled arterial PaCO₂ | `farkas_simplified_93_v1` | `EXTERNALLY_EVALUATED` | Jörg et al. 2023 | Component-only evaluation; source spectrum incomplete |
| Calculated HCO₃ | Henderson–Hasselbalch (`0.0307`, `6.095`) | `DERIVED_CALCULATION` | Krbec et al. 2022 verification | Calculated, not measured or serum total CO₂ |
| Candidate state set | `stewartlight_boston_ruleset_v1` | `IMPLEMENTED_SOFTWARE_RULESET` | Repository compatibility behavior | Not an adjudicated clinical standard |
| Serum anion gap | Na − Cl − serum total CO₂ | `DERIVED_CALCULATION` | Documented repository formula | Serum chemistry only |
| Optional Stewart partition | Pinned structured upstream helper | `IMPLEMENTED_SOFTWARE_RULESET` | `stewartlight@f277cac` | Venous basis; requires supplied venous base excess and same-time chemistry |

## Candidate arterial pH–PaCO₂ model

The retained simplified model has ID `farkas_simplified_93_v1` and reference saturation 93
percentage points. With same-sample venous saturation `SvO₂` in percentage points, the Explorer
computes:

```text
modeled pH     = measured VBG pH + 0.0011 × (93 − SvO₂)
modeled PaCO₂  = measured PvCO₂ − 0.22 × (93 − SvO₂)
```

The pH component carries `DERIVATION_ONLY` evidence. Its displayed range is the retained
approximately ±0.03 source-reported error band; it is not a patient-specific probability or
confidence interval.

The PaCO₂ component carries `EXTERNALLY_EVALUATED` evidence with the recorded Jörg profile
limitations. The error convention is `estimate_minus_arterial_reference`. The retained profiles
are:

| Supplemental oxygen context | Error lower / upper (mmHg) |
| --- | --- |
| `NO` | −5.83 / +5.32 |
| `YES` | −8.74 / +9.20 |
| `UNKNOWN` | −8.74 / +9.20, conservative profile |

The external evaluation of PaCO₂ is not validation of modeled pH, calculated HCO₃, the combined
Explorer, individual arterial conversion, classification, treatment equivalence, or VBG–ABG
interchangeability. The source spectrum is not fully established by this product, so the result
always retains that limitation rather than inventing an extrapolation cutoff.

The PaCO₂ formula and evaluation profile are documented in Jörg et al. 2023
([doi:10.1186/s40635-023-00564-w](https://doi.org/10.1186/s40635-023-00564-w)). The retained pH
formula came from an unpublished/redacted 2012 Farkas derivation manuscript
([author-hosted redacted copy](https://emcrit.org/wp-content/uploads/2017/01/ABGVBGmsREDACTED.pdf),
retrieved 2026-08-02) and remains `DERIVATION_ONLY`. No explicit manuscript reuse license or
external peer-reviewed pH validation was identified. The repository implements independently
expressed equations/constants only; it does not contain manuscript text, figures, or tables.

## Calculated HCO₃ and state ruleset

When a value is calculated from pH and PaCO₂, the Explorer uses the retained
Henderson–Hasselbalch relation with `0.0307` and `6.095`. It is labelled
`DERIVED_CALCULATION`, remains distinct from a measured or reported blood-gas HCO₃, and is never
replaced with serum total CO₂.

The retained Boston compatibility engine is identified as `stewartlight_boston_ruleset_v1`. It is
an `IMPLEMENTED_SOFTWARE_RULESET`, not an adjudicated clinical gold standard. The Explorer uses a
certified terminal-path feasibility implementation over its decision surfaces rather than a finite
grid to derive possible states. It evaluates both chronicity branches by design.

## Serum chemistry and Stewart context

Serum anion gap is calculated as `Na − Cl − serum total CO₂`. Albumin-corrected anion-gap context
is calculated only when albumin is supplied and records its calculation metadata. Neither
calculation produces an arterial gas value.

The optional `VENOUS_BASIS` Stewart partition is calculated by the pinned upstream
specimen-neutral structured helper from supplied VBG pH, measured venous base excess, and
same-timepoint chemistry. It does not infer arterial SBE or accept PvCO₂, blood-gas HCO₃, or
serum total CO₂ as a partition operand.

## Source identifiers and restrictions

The local evidence descriptors preserve source identifiers such as `farkas_2012_public_manuscript`,
`jorg_2023`, `krbec_2022`, and `clsi_c46_a2_official_record`. These identifiers document the
current evidence boundary; they do not transfer rights or authorize copying restricted text,
figures, tables, standards, or unpublished material. See [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

## Verification versus validation

The deterministic synthetic matrix checks formula stability, model-domain refusals, partial-result
composition, set-predicate semantics, and browser contracts. It does not estimate clinical bias,
limits of agreement, coverage, sensitivity, specificity, calibration, subgroup performance, or
patient outcomes. No protected or patient-derived validation dataset is included or executed in
this repository. Those questions remain future external scientific work.
