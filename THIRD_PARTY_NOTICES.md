# Third-party notices

Repository-authored code is licensed under [MIT](LICENSE). This file records attribution and
source boundaries; it does not grant rights in third-party materials, constitute legal advice,
create clinical validation, or imply endorsement.

## Pyodide

The static browser bundle includes a self-hosted subset of Pyodide 0.29.3 under
`web/vendor/pyodide/0.29.3/`. Its component inventory and license notices are stored in that
directory and verified by `scripts/verify_pyodide_vendor.py`. The inventory is not a complete
software bill of materials or freedom-to-operate opinion.

## Upstream Stewart Light dependency

The Explorer stages the MIT-licensed `reblocke/stewart-light` Python dependency pinned at commit
`f277cac54801d85366cbadbf11804f6643f6a869`. It uses the specimen-neutral structured Stewart
partition helper and does not include a second editable copy of the upstream ABG application. See
the [upstream repository](https://github.com/reblocke/stewart-light) for its source and notices.

## Scientific sources

- Jörg M, Öster M, Wretborn J, Wilhelms DB. Agreement of pCO₂ in venous to arterial blood gas
  conversion models in undifferentiated emergency patients. *Intensive Care Med Exp.* 2023;11:80.
  [doi:10.1186/s40635-023-00564-w](https://doi.org/10.1186/s40635-023-00564-w). CC BY 4.0. It is
  cited for the Farkas PaCO₂ formula and component-specific evaluation boundary, not validation of
  modeled pH or the full Explorer.
- Krbec M, et al. Non-carbonic buffer power of whole blood is increased in experimental metabolic
  acidosis: an in-vitro study. *Front Physiol.* 2022;13:1009378.
  [doi:10.3389/fphys.2022.1009378](https://doi.org/10.3389/fphys.2022.1009378). CC BY 4.0. It is
  cited as an open verification of the retained Henderson–Hasselbalch constants.
- The Farkas pH component is retained from an unpublished/redacted 2012 derivation manuscript
  shared by its author at
  `https://emcrit.org/wp-content/uploads/2017/01/ABGVBGmsREDACTED.pdf` (retrieved 2026-08-02).
  No explicit reuse license was found for that manuscript. This repository independently
  re-expresses only the equations/constants approved by the owner; it does not redistribute the
  manuscript, its prose, figures, tables, or layout. The component remains labeled
  `DERIVATION_ONLY`, and this release does not claim peer-reviewed external pH validation.
- The Boston-style classifications are repository-authored compatibility implementations of
  common acid–base rules. They are not presented as copied source text, an adjudicated authority,
  or a clinical gold standard.

No third-party scientific-source figures, tables, full-text articles, publisher layouts,
standards text, or source artifacts are included. The self-hosted Pyodide runtime is intentionally
distributed under the component licenses and source notices inventoried in its vendor directory.
The cited authors, publishers, institutions, and licensors have not endorsed this software or any
clinical use.

## Owner release attestation

The repository owner documented the public source-and-Pages distribution decision in
[docs/PUBLIC_RELEASE_REVIEW.md](docs/PUBLIC_RELEASE_REVIEW.md). That attestation records the
owner's authority and review decision; it is not independent legal advice, a publisher license,
regulatory clearance, clinical approval, or a finding of commercial/operational clinical
suitability. The MIT license governs repository-authored code without an additional
research-purpose restriction.
