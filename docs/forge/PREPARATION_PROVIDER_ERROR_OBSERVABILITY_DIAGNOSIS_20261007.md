# Preparation Provider Error Observability Diagnosis

Date: 2026-10-07 (Asia/Shanghai)

## Scope

This diagnosis covers the provider-error projection boundary exposed by
`task_13315d0d962a45f5`. It applies to arbitrary preparation providers and does
not encode benchmark, object, sensor, candidate, or arm identities.

## Observed Projection Loss

The Adapter persisted the exact exception in `preparation-metrics`:

```text
ValueError: materialized artifact conflicts with runtime evidence
```

The public Query result instead contained only:

```text
preparation_provider_error: manipulation preparation provider failed
```

The Core endpoint behaves correctly for a genuinely unknown provider
exception, but the Adapter already owns and understands artifact publication.
Allowing its expected conflict to escape as a bare `ValueError` discards the
code, owner, retryability, recommended action, and bounded diagnostic path.

## Required Contract

The Adapter boundary must translate publication conflicts to
`PreparationProviderError` with:

- a stable provider-neutral code;
- `failure_owner=runtime_provider`;
- `retryable_in_revision=false`;
- `requires_replan=false`;
- `recommended_action=fix_runtime_contract`;
- the conflicting relative artifact path and preparation-build diagnostic
  location, without leaking credentials or arbitrary host paths.

Unknown exceptions remain flattened by the Core. Only errors recognized by the
owning Adapter receive specific public diagnostics.

## Convergence and Safety

The structured result lets the existing AgentLoop stop deterministically. It
does not authorize automatic retry, replan, observation refresh, candidate or
arm switching, or Action execution. Artifact immutability remains fail-closed,
and the failure occurs with zero simulator steps.
