# Interpretation specification

## One result contract

The only live request schema is `vbg_explorer_request/1.0`; the only live result schema is
`vbg_explorer_result/1.0`. There is no migration or fallback behavior for superseded pre-release
schemas.

The public Python entry point is `vbg_interpreter.interpret_vbg(request)`. The browser calls the
same contract through `vbg_interpreter.browser_adapter.interpret_browser_request_json`.
Every result's provenance includes the producing Explorer software version. A deployed static
bundle additionally publishes its exact Git commit in `release-manifest.json`.

## State enumeration

If `candidate_arterial_region.status` is `AVAILABLE`, the Explorer passes its closed pH–PaCO₂
rectangle to the certified terminal-path engine. That engine evaluates both
`CHRONIC_FLAGGED` and `NOT_CHRONIC_FLAGGED` branches, proves a terminal ruleset path feasible or
infeasible, and returns every feasible `StateSignature` in canonical order.

The result includes:

- `coverage_method_id = CERTIFIED_TERMINAL_PATH_FEASIBILITY`;
- decision-surface and terminal-path counts;
- precision used for the proof; and
- a deterministic display-only coordinate sample map.

If certification fails, `enumeration_status` is `CERTIFICATION_FAILED` and no possible-state list
is emitted. Every feature is explicitly `NOT_EVALUABLE`, never silently treated as excluded. If no
candidate region is available, `enumeration_status` is `NOT_EVALUATED` and the same explicit
non-evaluability rule applies.

The coordinate view is not the inference engine. Its x-axis is candidate arterial PaCO₂; its
y-axis is candidate arterial pH. Sample markers exist for explanation, hover/focus, and a visual
map only. Neither the number of markers nor their occupied area has probability, frequency,
confidence, or likelihood meaning.

## Set predicates

Every user-facing conclusion maps to one of these typed statuses:

| Status | Exact predicate |
| --- | --- |
| `PRESENT_ACROSS_ALL_MODELED_STATES` | The feature occurs in every feasible signature. |
| `POSSIBLE_IN_SOME_MODELED_STATES` | The feature occurs in at least one but not every feasible signature. |
| `EXCLUDED_WITHIN_MODELED_STATE_SPACE` | The feature occurs in no feasible signature. |
| `NOT_EVALUABLE` | No valid modeled state space exists, the feature is outside scope, or a feasible ruleset category does not resolve that feature. |

The engine currently publishes predicates for acidemia/near-normal pH/alkalemia, each retained
primary-process category, expected-compensation and measured-versus-expected categories,
respiratory and metabolic component features where explicit ruleset conditions support them, the
mixed-process flag, and both chronicity branches. It does not infer a component from an otherwise
ambiguous label. If any feasible signature has a primary category that does not resolve respiratory
or metabolic components, all component conclusions are `NOT_EVALUABLE`; the Explorer does not turn
that unresolved category into a false component exclusion.

“Excluded” must always retain the phrase “within the modeled state space” in user-facing copy. It
does not exclude a disorder outside the current model inputs, scope, or software ruleset.

## Point orientation

The modeled point is displayed only for orientation. It never determines the headline when more
than one state is feasible. A displayed point is modeled, not an arterial measurement.

## Chemistry and longitudinal synthesis

Chemistry and longitudinal results are parallel lanes. A chemistry observation may be described as
concordant, discordant, or incomplete only when a future rule documents its predicate. In v1,
serum total CO₂ does not narrow the modeled arterial state set. A prior observation remains
contextual and does not delete a chronicity branch.

The information-gain list contains typed, non-directive missing information that could reduce an
identified limitation. It may mention arterial confirmation when needed, same-sample venous
saturation, model context, albumin, base excess, or a comparable prior observation. It is not a
treatment recommendation.
