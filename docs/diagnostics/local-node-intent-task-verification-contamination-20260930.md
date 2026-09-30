# Local Node Intent and Task Verification Semantic Contamination

## Problem

Plan materialization may place two different semantic scopes into one node's input bindings:

- node-local structured `intent`, describing the immediate tool operation;
- task-level verification `goal` and `success_criteria`, describing final acceptance of the whole AgentTask.

When both are flattened onto the same node, Coordinator selection correctly rejects the node with `invalid_node_semantics: nested and flat node intent semantics conflict`.

## Concrete Failure

The affected node had a valid structured local intent for preparing one collision-checked acquire route. Its flat `goal` and `success_criteria`, however, contained the final three-object arrangement and verification contract. The two scopes were not equivalent, so `planning_dispatch` refused to build `manipulation_intent_v2`.

## Architectural Diagnosis

The validator is not the defect. It protects Coordinator semantics from ambiguous or contradictory action intent. The defect is upstream at plan materialization, where task-level verification semantics are copied into every node despite the node already owning a structured local intent.

Ownership must remain separated:

- AgentTask verification contract owns final-task goal and acceptance criteria.
- Plan node structured intent owns the immediate operation semantics.
- Legacy flat-only nodes may continue receiving flat goal and success criteria for compatibility.

## Required Fix

At plan materialization, inject task-level flat semantics only when the node does not provide a structured intent mapping. Do not weaken selection validation, synthesize opaque references, or add a new gate, digest, hash, or RGB-specific exception.

## Acceptance Criteria

1. Structured local intent remains byte-for-byte semantically intact through materialization.
2. Task verification goal and criteria are not flattened onto structured-intent nodes.
3. Coordinator selection produces valid `manipulation_intent_v2` for the node.
4. Legacy nodes without structured intent retain their flat semantics.
5. Existing safety, freshness, authorization, planning admission, and terminal-result gates remain unchanged.

## Seven-Dimension Review Baseline

The completed implementation will be reviewed for: architecture and ownership, functional correctness, backward compatibility, safety and authorization, failure and recovery semantics, tests and reproducibility, and maintainability and release integration.
