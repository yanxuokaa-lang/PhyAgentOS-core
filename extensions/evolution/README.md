# PAOS Evolution Extension

See the [closed-loop algorithm review](../../docs/forge/EVOPHY_CLOSED_LOOP_REVIEW.md)
for tested lifecycle behavior and outstanding real-provider evaluation work.
Transition projections should supply explicit `depends_on` edges. TRACE does
not infer dependencies or joint causes from observation timestamps or shared
images. Local advice loaded by a future activation is tracked separately from
Runtime binding identity; loading does not prove behavioral adoption.

`evolution` is an optional, independently packaged host for self-evolution
methods. `evolution.methods.evophy` is the first method implementation. The
package consumes provider-neutral episode projections and emits non-authoritative
revision candidates; it does not own PAOS task state, Skill promotion, planning,
verification, or execution.

## Independent development environment

```bash
cd extensions/evolution
uv venv --python 3.11 .venv
uv sync --dev
uv run pytest -q
uv run ruff check evolution tests
uv build
```

The local `.venv` is excluded by the repository `.gitignore`. This environment
isolates extension development, tests, and builds from PAOS Core. In-process
deployment installs the built wheel into the PAOS host environment and injects
an `EvolutionExtension` through the episode-closed hook.

A dedicated worker process is needed when an evolution method introduces
dependency conflicts, crash-isolation requirements, or sustained resource use.
That deployment keeps this API and adds a transport adapter at the host boundary.

## Method boundary

New methods live under `evolution/methods/<method_id>/` and implement
`EvolutionMethod`. Candidate and evaluation identities include `method_id`, so
methods do not share receipts or future-use observations. Candidate identity is
derived from the canonical method, Skill revision, workflow transition, patch,
and applicability payload, so equivalent proposals aggregate across episodes
while different patch content remains isolated.

## Settle physical outcomes

`ConsequenceSettler` turns timestamped provider evidence into one observation
per expected transition predicate. A window remains `pending` until its
deadline or an explicit provider, terminal, or interruption close. At close,
the latest evidence must meet the configured coverage threshold; missing,
low-coverage, or same-time conflicting evidence settles as `unknown`.

```python
from evolution import (
    ConsequenceSettler,
    OutcomeEvidenceSample,
    OutcomeWindow,
    SettlementTarget,
)

observations = ConsequenceSettler().settle(
    targets=(
        SettlementTarget(
            transition_id="place",
            predicate="object-stable",
            outcome_window=OutcomeWindow(
                opened_at_ms=1_000,
                deadline_at_ms=3_000,
            ),
        ),
    ),
    samples=provider_evidence_samples,
    at_ms=3_000,
)
```

The provider adapter owns the physical meaning of each
`OutcomeEvidenceSample`. The settler only applies window, ordering, coverage,
and conflict semantics; it neither polls sensors nor invokes a Tool.

## Compose a provider-neutral episode projection

The host supplies task identity, the Skill supplies transition expectations,
and the provider adapter supplies observed outcomes. The extension combines
those three read-only views; none of the projection ports owns execution state.

```python
from evolution import EvolutionExtension, EvolutionMethodRegistry
from evolution.methods.evophy import EvoPhyMethod
from evolution.projection import ComposedEpisodeProjectionPort, EpisodeMetadata

projection_port = ComposedEpisodeProjectionPort(
    metadata_projector=lambda episode: EpisodeMetadata(
        episode_id=episode.episode_id,
        root_task_id=episode.root_task_id,
    ),
    transition_port=skill_transition_projector,
    outcome_port=provider_outcome_projector,
)
extension = EvolutionExtension(
    registry=EvolutionMethodRegistry([EvoPhyMethod()]),
    projection_port=projection_port,
    candidate_lifecycle=host_candidate_lifecycle,
    event_sink=record_evolution_event,
)
```

Inject `extension` into the PAOS composition root as `evolution_extension`.
`host_candidate_lifecycle` implements the `CandidateLifecyclePort.submit`
method and maps a non-authoritative proposal into the existing Skill or
workflow candidate lifecycle. The extension never promotes a candidate itself;
the host remains responsible for support aggregation, review, activation, and
rollback. `candidate_sink` remains available for observation-only integrations.
Projection, method, and sink failures are reported through the event sink and
do not change the persisted episode or task verdict.

PAOS hosts may use `PhyAgentOS.agent.experience.evolution_composition.compose_evolution_extension`
as the standard composition root. Pass an existing extension, or explicitly
provide `registry` and `projection_port` so the host chooses the provider and
Skill projection ports. The helper wires the existing `ExperienceStore` and
candidate lifecycle, records extension events in that store, is idempotent, and
returns `None` when the optional `evolution` distribution is not installed.

For a Skill candidate, call `on_candidate_evaluated(...)` for each
`EvaluationReceipt` and `on_candidate_selected(...)` for the evaluator's
`EvaluationDecision`; the host lifecycle records both. An explicit host reviewer may then call
`ExperienceCoordinator.review_evolution_skill_candidate(...)` only after the
configured independent support and the current receipt set support a `promote`
decision. The call uses the existing Skill writer and rollback path; it is not
an extension-side promotion API.

## Candidate evaluation

Candidate generation and candidate selection are separate. The evaluator
requires matched, held-out, and hazard receipts with explicit parent/candidate
metrics. Fixed policy weights make the success, cost, side-effect, and
interference trade-off inspectable.

```python
from evolution.evaluation import CandidateEvaluator, SelectionPolicy

policy = SelectionPolicy(
    success_gain_weight=1.0,
    action_cost_weight=0.05,
    time_cost_weight_per_second=0.02,
    side_effect_rate_weight=0.5,
    interference_weight=1.0,
    minimum_utility=0.0,
)
decision = CandidateEvaluator(policy=policy).decide(
    proposal,
    receipts=evaluation_receipts,
)
```

A missing split, an unknown verdict, or missing before/after metrics keeps a
candidate on hold. A failed matched, held-out, or hazard evaluation rejects it.
Promotion is only a decision request; the existing host review and activation
lifecycle remains authoritative.

The host records every Future-use observation, but recomputes aggregate metrics
only when the set of complete parent/candidate pairs changes. An unpaired
observation remains available for its later counterpart without retriggering a
comparison for unchanged pairs.

## Reproducible evaluation artifacts

`EvaluationArtifactWriter` creates one non-overwriting directory per run under
the caller-selected output root:

```text
<output-root>/<run-id>/
├── manifest.json
├── receipts.jsonl
├── decisions.json
├── future-use.json
└── metrics.json
```

The manifest records code revision, config reference, random seed, dataset
name/version, checkpoint reference, task order, method IDs, and the selection
policy. Compare runs using `metrics.json`, then inspect `decisions.json` and
`future-use.json` for candidate-level and parent/candidate deltas. Fake-facts
tests validate the mechanics only; benchmark and robot results must come from
independent evaluation artifacts.
