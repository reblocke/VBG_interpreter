# ADR 0002: Publish a history-free canonical repository

## Status

Accepted 2026-08-02.

## Context

Private development history contains superseded milestone, governance, validation, release-gate,
issue, pull-request, and workflow material that is not part of the lightweight Explorer product.
Changing the existing repository's visibility would publish that unrelated history and metadata.
The desired public identity remains `reblocke/VBG_interpreter`.

## Decision

Rename the existing private repository to `VBG_interpreter-private-archive-20260802`. Create a new
public `reblocke/VBG_interpreter` from the exact reviewed source tree with one history-free root
commit and make it the canonical repository for future development.

The public repository hosts a GitHub Pages bundle built from the same commit and publishes
`v0.1.0` as a prerelease. The private archive remains private and becomes read-only only after the
public repository, required checks, Pages site, release manifest, and release are verified.

## Consequences

- Public users receive the current product without superseded private history or workflow logs.
- Public and private repositories have unrelated Git histories by design.
- The source commit recorded by the public release and Pages manifest is the public root commit,
  not the private merge commit from which its tree was exported.
- Future work belongs in the public canonical repository; the private repository is historical
  evidence only.
- History minimization does not change scientific evidence, licensing scope, or clinical status.
