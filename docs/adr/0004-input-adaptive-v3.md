# ADR 0004: Input-adaptive v0.3 calculations

Accepted 2026-09-12 by the owner during implementation planning. This supersedes live v2
interpretation behavior in ADRs 0001 and 0003; it does not revise their historical record or
ADR 0002's public/private history boundary.

Use independently gated capabilities for any available VBG measurements and optional chemistry.
Remove individual arterial rectangles based on population marginal summaries, Boston enumeration,
and prior-observation contracts. Keep categorical screening NOT_CONFIGURED until separately
approved. Retain neutral measured-pH reference positioning without a venous-normal claim.

Unknown model applicability can produce an explicitly uncertain PaCO2 estimate, but confirmed
same-sample saturation and source-measured PvCO2 remain hard prerequisites. Known unfavorable
sampling/context withholds the estimate.

The owner extended the ticket to calculate missing standard base excess at assumed normothermia,
selected the classic Van Slyke equation, and authorized derived venous SBE to feed an otherwise
eligible Stewart partition. Preserve reported-standard-SBE precedence, BE basis, complete derived
provenance, and the separate measured-pH and same-time-chemistry requirements. No upstream formula
copy or dependency change is needed; the pinned helper does not calculate SBE from gas inputs.

The owner also approved merging both outstanding dependency PRs, preserving old private work in
verified backups, finishing with one active public-main checkout, and merging/deploying v0.3
through protected main after review and checks. No tag, GitHub Release, private-history
publication, or clinical-validation claim is included.

The v0.4 estimate-selection and presentation revision is recorded in [ADR 0005](0005-known-best-guess-v4.md).
