# ADR 0007: Component selection and qualified HH chains

Date: 2026-09-12. Status: accepted for v0.6 implementation.

The owner-approved v0.6 plan supersedes the measured-only converter and Unknown-sample fixed
rules in ADRs 0005/0006. One small Python selector consumes existing HH completion; a global
Farkas/fixed mode would incorrectly couple independent pH/CO2 outputs. No new equations or
upstream Boston changes are introduced.

Unknown plus saturation selects Farkas under a visible peripheral assumption, without changing
sample identity. Known Central retains the fixed heuristic. Two appropriate same-gas coordinates
may support an explicitly unvalidated chain. Original inputs, units, derivation and formula
versus case evidence remain distinct; no reconstruction overwrites a supplied coordinate.

Agreement status is separate from point status. Reconstructed PvCO2 receives no empirical range;
reconstructed pH does not remove a supplied-PvCO2 range. Positive points survive nonphysical
endpoints; selected numerical failure never triggers a method fallback. Only supplied usable
coordinates supply independent physiology bounds. Best guess plotting uses Python suitability.

The owner explicitly selected retaining finite chained estimates, plots and provisional
interpretation when Blood gas HCO3 alone has a sanity warning. Existing supplied pH/PvCO2
warning propagation remains, including dependencies through reconstructed coordinates.
No new derived-axis clinical cutoff, confirmation or questionnaire is added.

The result schema becomes 6.0; the unchanged exact-key request stays 5.0. Existing release
metadata supplies the footer identity, checked against the runtime package version. This is not
an asset integrity platform. Deployment/merge remains separately authorized under the existing
reviewed PR workflow. Synthetic matrix/browser verification does not establish clinical validity.
