"""TRACE transition attribution from PULSE records."""

from __future__ import annotations

from collections import defaultdict

from pydantic import Field

from evolution.api import EvolutionModel, OwnerHypothesis, PulseRecord, TraceHypothesis, TraceResult


class TracePolicy(EvolutionModel):
    minimum_coverage: float = Field(default=0.5, ge=0.0, le=1.0)
    violation_weight: float = Field(default=2.0, ge=0.0)
    unknown_weight: float = Field(default=0.5, ge=0.0)
    coverage_weight: float = Field(default=1.0, ge=0.0)
    downstream_weight: float = Field(default=0.25, ge=0.0)
    minimum_owner_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    score_primary: bool = False


class TraceAttributor:
    def __init__(self, *, policy: TracePolicy | None = None) -> None:
        self.policy = policy or TracePolicy()

    def attribute(self, episode_id: str, records: tuple[PulseRecord, ...]) -> TraceResult:
        grouped: dict[str, list[PulseRecord]] = defaultdict(list)
        for record in records:
            grouped[record.transition_id].append(record)

        hypotheses: list[TraceHypothesis] = []
        ordered = sorted(grouped.items(), key=lambda item: min(row.order for row in item[1]))
        ancestors: dict[str, set[str]] = {}
        for transition_id, rows in ordered:
            dependencies = {dep for row in rows for dep in row.depends_on}
            ancestors[transition_id] = dependencies | {
                ancestor for dep in dependencies for ancestor in ancestors.get(dep, ())
            }
        violated_transitions = {
            transition_id
            for transition_id, rows in ordered
            if any(
                row.observed == "violated" and row.evidence_coverage >= self.policy.minimum_coverage
                for row in rows
            )
        }
        unknown_predicates: list[str] = []

        for transition_id, rows in ordered:
            order = min(row.order for row in rows)
            violations = [
                row
                for row in rows
                if row.observed == "violated"
                and row.evidence_coverage >= self.policy.minimum_coverage
            ]
            unknowns = [
                row
                for row in rows
                if row.observed in {"unknown", "pending"}
                or row.evidence_coverage < self.policy.minimum_coverage
            ]
            unknown_predicates.extend(f"{transition_id}:{row.predicate}" for row in unknowns)
            selected = violations or unknowns
            if not selected:
                continue
            state = "violated" if violations else "unknown"
            downstream = tuple(
                later_id
                for later_id, later_rows in ordered
                if transition_id in ancestors[later_id] and later_id in violated_transitions
            )
            coverage = max(row.evidence_coverage for row in selected)
            base_weight = (
                self.policy.violation_weight if state == "violated" else self.policy.unknown_weight
            )
            score = (
                base_weight
                + self.policy.coverage_weight * coverage
                + self.policy.downstream_weight * len(downstream)
            )
            owner_hypotheses_by_owner: dict[str, OwnerHypothesis] = {}
            for row in selected:
                for owner_hypothesis in row.owner_hypotheses:
                    current = owner_hypotheses_by_owner.get(owner_hypothesis.owner)
                    if current is None or owner_hypothesis.confidence > current.confidence:
                        owner_hypotheses_by_owner[owner_hypothesis.owner] = owner_hypothesis
            owner_hypotheses = tuple(
                sorted(
                    (
                        item
                        for item in owner_hypotheses_by_owner.values()
                        if item.confidence >= self.policy.minimum_owner_confidence
                    ),
                    key=lambda item: (-item.confidence, item.owner),
                )
            )
            owner = (
                owner_hypotheses[0].owner
                if owner_hypotheses
                else (
                    "unknown" if any(row.owner_hypotheses for row in selected)
                    else next((row.owner for row in selected if row.owner != "unknown"), "unknown")
                )
            )
            reversibility = "unknown"
            if any(row.reversibility == "irreversible" for row in selected):
                reversibility = "irreversible"
            elif any(row.reversibility == "reversible" for row in selected):
                reversibility = "reversible"
            hypotheses.append(
                TraceHypothesis(
                    transition_id=transition_id,
                    order=order,
                    predicates=tuple(dict.fromkeys(row.predicate for row in selected)),
                    state=state,
                    score=score,
                    evidence_coverage=coverage,
                    owner=owner,
                    owner_hypotheses=owner_hypotheses,
                    reversibility=reversibility,
                    downstream_violations=downstream,
                )
            )

        if self.policy.score_primary:
            hypotheses.sort(
                key=lambda item: (
                    item.state != "violated",
                    -item.score,
                    item.order,
                    item.transition_id,
                )
            )
        else:
            hypotheses.sort(
                key=lambda item: (
                    item.state != "violated",
                    item.order,
                    -item.score,
                    item.transition_id,
                )
            )
        actionable = [
            item
            for item in hypotheses
            if item.state == "violated" and item.owner in {"workflow", "planner", "perception"}
        ]
        adjacency = {item.transition_id: set() for item in actionable}
        for index, left in enumerate(actionable):
            left_rows = grouped[left.transition_id]
            left_refs = {
                (hyp.owner, ref) for row in left_rows for hyp in row.owner_hypotheses
                if hyp.confidence >= self.policy.minimum_owner_confidence
                for ref in hyp.evidence_refs
            }
            for right in actionable[index + 1 :]:
                right_rows = grouped[right.transition_id]
                right_refs = {
                    (hyp.owner, ref) for row in right_rows for hyp in row.owner_hypotheses
                    if hyp.confidence >= self.policy.minimum_owner_confidence
                    for ref in hyp.evidence_refs
                }
                related = left.transition_id in ancestors[right.transition_id] or right.transition_id in ancestors[left.transition_id]
                if related and left_refs & right_refs:
                    adjacency[left.transition_id].add(right.transition_id)
                    adjacency[right.transition_id].add(left.transition_id)
        joint_sets: list[tuple[str, ...]] = []
        visited: set[str] = set()
        order_by_id = {item.transition_id: item.order for item in actionable}
        for transition_id in adjacency:
            if transition_id in visited or not adjacency[transition_id]:
                continue
            pending = [transition_id]
            component: list[str] = []
            while pending:
                current = pending.pop()
                if current in visited:
                    continue
                visited.add(current)
                component.append(current)
                pending.extend(adjacency[current] - visited)
            joint_sets.append(tuple(sorted(component, key=lambda item: (order_by_id[item], item))))
        return TraceResult(
            episode_id=episode_id,
            ranked=tuple(hypotheses),
            joint_cause_sets=tuple(joint_sets),
            unknown_predicates=tuple(dict.fromkeys(unknown_predicates)),
        )


__all__ = ["TraceAttributor", "TracePolicy"]
