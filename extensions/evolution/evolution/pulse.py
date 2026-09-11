"""PULSE outcome logging over provider-neutral episode projections."""

from __future__ import annotations

from evolution.api import EpisodeProjection, PulseRecord


class PulseLogger:
    def build(self, episode: EpisodeProjection) -> tuple[PulseRecord, ...]:
        observations = {(item.transition_id, item.predicate): item for item in episode.observations}
        records: list[PulseRecord] = []
        for transition in sorted(episode.transitions, key=lambda item: item.order):
            for predicate in transition.expected_predicates:
                observation = observations.get((transition.transition_id, predicate))
                if observation is None:
                    records.append(
                        PulseRecord(
                            transition_id=transition.transition_id,
                            order=transition.order,
                            depends_on=transition.depends_on,
                            predicate=predicate,
                            observed="unknown",
                            evidence_coverage=0.0,
                            action_cost=episode.action_cost,
                            time_cost_ms=episode.time_cost_ms,
                        )
                    )
                    continue
                observed = observation.state
                window_closed = (
                    observation.outcome_window.closed
                    if observation.outcome_window is not None
                    else observation.outcome_window_closed
                )
                unexpected_side_effects = tuple(
                    effect
                    for effect in observation.side_effects
                    if effect not in transition.allowed_side_effects
                )
                if not window_closed:
                    observed = "pending"
                elif observed == "pending":
                    observed = "unknown"
                elif observed == "satisfied" and unexpected_side_effects:
                    observed = "violated"
                records.append(
                    PulseRecord(
                        transition_id=transition.transition_id,
                        order=transition.order,
                        depends_on=transition.depends_on,
                        predicate=predicate,
                        observed=observed,
                        evidence_coverage=observation.evidence_coverage,
                        settled_at_ms=(
                            (
                                observation.outcome_window.closed_at_ms
                                if observation.outcome_window is not None
                                else observation.observed_at_ms
                            )
                            if observed != "pending"
                            else None
                        ),
                        side_effects=observation.side_effects,
                        unexpected_side_effects=unexpected_side_effects,
                        reversibility=observation.reversibility,
                        owner=observation.owner,
                        owner_hypotheses=observation.owner_hypotheses,
                        evidence_refs=observation.evidence_refs,
                        action_cost=episode.action_cost,
                        time_cost_ms=episode.time_cost_ms,
                    )
                )
        return tuple(records)


__all__ = ["PulseLogger"]
