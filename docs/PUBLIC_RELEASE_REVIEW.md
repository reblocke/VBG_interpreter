# Public release owner review

Record schema: `owner_public_preview_attestation/1.0`

## Decision record

- Decision date: 2026-08-02
- Owner/decision maker: Brian Locke (`github:reblocke`)
- Release: `v0.1.0` public research preview
- Authorized surfaces: history-free public source repository and static GitHub Pages site
- Historical repository: preserve privately, rename to
  `VBG_interpreter-private-archive-20260802`, then archive read-only after cutover verification

## Owner attestation

The owner states that they control the repository-authored code and data decisions and have
reviewed and approved public research/educational distribution of this implementation. The review
covered the simplified Farkas constants and provenance, Boston-style compatibility implementation,
Jörg and Krbec attribution, the pinned MIT-licensed Stewart Light dependency, the self-hosted
Pyodide notices, and the repository-authored documentation and browser assets.

No external rights or legal-opinion record exists for this release. This document is therefore an
owner attestation, not independent legal advice, a publisher or standards license, a
freedom-to-operate opinion, regulatory clearance, clinical approval, third-party endorsement, or
a finding of readiness or suitability for commercial/operational clinical deployment. The
research/educational intended-use boundary does not add a restriction to the MIT license for
repository-authored code.

## Scope of authorization

The owner authorizes:

- publishing the reviewed current tree without its private development history;
- hosting the same reviewed static bundle on GitHub Pages;
- publishing a `v0.1.0` prerelease bound to the exact public source commit; and
- accepting synthetic, non-sensitive research-software reports and contributions.

The owner does not authorize:

- publishing the old private Git history, pull requests, issues, logs, or governed records;
- including third-party scientific full text, figures, tables, standards text, or source
  artifacts beyond the separately licensed runtime inventory;
- entering or publishing PHI, real patient values, protected datasets, or credentials;
- clinical, diagnostic, treatment, ABG-substitution, analyzer-equivalence, management, or
  commercial/operational clinical-suitability claims; or
- presenting this release as external clinical validation.

## Required release controls

Publication is conditional on all of the following:

1. `make verify` and `make validation` pass on the reviewed source commit.
2. The public repository starts from a history-free commit authored with the owner's GitHub
   noreply identity.
3. Main-branch protection requires the `verify` and `validation` checks and pull requests. The
   owner approved a zero-independent-reviewer rule for this preview.
4. The Pages workflow checks live public visibility and the current `main` commit immediately
   before deployment and publishes only the generated static bundle.
5. The live release manifest identifies the exact source commit.
6. The public site, repository metadata, security reporting, license, citation, intended use, and
   caveats are verified after cutover.
7. Only after the public cutover passes is the private historical repository archived read-only.

This release decision does not change any evidence tier or scientific limitation.
