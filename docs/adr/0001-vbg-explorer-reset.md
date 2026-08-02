# ADR 0001: Reset to one set-valued VBG Explorer

## Status

Accepted. The later public-deployment decision is recorded separately in ADR 0002.

## Decision

Replace the former multi-product ABG/VBG application and its prospective validation/release
platform with one lightweight VBG Acid–Base Explorer.

The Explorer has one request schema, one result schema, one interpretation entry point, and one
browser workflow. It accepts current VBG and serum chemistry information, optional limited
context, and at most one prior observation. It reports a set of compatible modeled states when
the arterialization model is available instead of forcing one arterial diagnosis.

The complete local ABG application is removed. The repository uses a pinned upstream
`stewartlight` dependency for the narrow structured Stewart partition helper and links to the
upstream ABG app for an ABG educational workflow.

The pinned dependency is the descendant `f277cac54801d85366cbadbf11804f6643f6a869` of the
specified compatibility baseline `d2b25089f998748a91abfea14c68c23ac9eed708`. The descendant
contains the small upstream helper extraction and specimen-neutral partition input needed to
avoid maintaining an editable ABG copy; upstream frozen legacy ABG fixtures verified that this
change did not alter ABG results.

The old protected-validation, public-export, signed-release, migration, model-registry, and
historical milestone machinery is removed from the live tree. Git history remains the archive.

## Consequences

- The Explorer is smaller and has one clear scientific/product boundary.
- Old unpublished pre-release schemas and browser routes intentionally stop working.
- Existing ABG product behavior belongs upstream instead of being maintained here.
- The reset preserves conservative VBG evidence limits, explicit provenance, certified state
  enumeration, and client-side privacy constraints.
- This simplification did not itself authorize deployment or generate clinical evidence. The
  later public-preview deployment decision is recorded in ADR 0002; it does not make the product
  clinically validated.
