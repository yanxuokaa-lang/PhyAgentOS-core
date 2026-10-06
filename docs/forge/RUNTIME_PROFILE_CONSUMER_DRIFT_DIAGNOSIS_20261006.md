# Runtime Profile Consumer Drift Diagnosis

## Scope

This diagnosis records the repeated `route_materialization_invalid` failure at the
RoboTwin `manipulation.prepare` boundary. It is based on the persisted facts for:

- AgentTask: `task_5f6efbc4e2d94061`
- active plan revision: `revision_f40331de076048e7`
- scene revision: `c97df2649a654ee2aba81dbde28d8c53-1`
- failed node: `red_prepare`
- failed Tool record: `tool_f6e3d10788c04a7b`
- retained materializer run: `preparation-builds/route-yxghy5xx`

This was a no-motion failure. The preparation node was a Query,
`invocation_id=null`, `world_change_started=false`, and no `object.acquire` or
`object.place` record exists.

## Persisted Event Chain

1. Current-task synchronized observation, understanding, capability discovery,
   entity binding, and external `task.goal` discovery succeeded.
2. The Coordinator injected the benchmark destination for the bound entity.
3. `red_propose` executed `grasp.propose` successfully and persisted 32 candidates.
4. `red_prepare` received the selected candidate record and capability evidence.
5. `PersistentRouteBuilder` invoked `materialize_complete_route.py` for candidate 0.
6. The materializer stopped before route construction with:

   ```json
   {
     "code": "route_materialization_invalid",
     "message": "runtime profile identity fields are invalid"
   }
   ```

7. `manipulation.prepare` returned `status=unavailable`,
   `prepared_candidates=[]`, and `motion_authorized=false`.

The failure is therefore after proposal generation but before workspace, IK,
collision, release, or retreat qualification. It is not a grasp-candidate
selection failure and it is not evidence that any object was moved.

## Root Cause

The deployed Runtime profile is valid and intentionally uses one synchronized
sensor set:

```yaml
sensor_refs: [camera/head, camera/front]
```

`runtime/robotwin_backend.py:load_runtime_profile` already accepts exactly one of
`sensor_ref` or `sensor_refs` and normalizes both forms. In contrast,
`scripts/materialize_complete_route.py:_load_runtime_identity` maintains a second,
older field whitelist that requires `sensor_ref` and rejects `sensor_refs` as an
unknown field.

The same profile consequently passes Runtime startup but deterministically fails
when the route materializer consumes it. Commit `d635af1` changed the shipped
profile and Runtime loader to multi-view operation without updating the independent
materializer schema.

## Why Existing Mechanisms Did Not Prevent It

- Git and package versions identify the code revision but do not make two handwritten
  consumer schemas equal.
- Python types validate each consumer locally but do not express that both consumers
  interpret the same profile.
- Startup tests covered the Runtime loader; the materializer test existed but was a
  known baseline failure rather than a release blocker.
- Retrying the Agent loop cannot alter a static parser whitelist, so every fresh task
  reaches the same preparation failure after paying the proposal cost again.

This is a duplicated source-of-truth defect. Removing that duplication does not add
a speculative gate.

## Architecture-Aligned Repair

The Adapter owns the Runtime profile contract. Create one dependency-light shared
profile module under `robotwin20_adapter` that:

- loads YAML with duplicate-key rejection;
- validates the versioned profile fields once;
- accepts exactly one of `sensor_ref` or `sensor_refs`;
- rejects empty, duplicate, or unsupported sensor references;
- normalizes both forms to `sensor_ref` plus an ordered `sensor_refs` tuple;
- validates task, embodiment, topology, identity, observation age, and optional
  static-camera fields;
- returns a normalized mapping without authorizing motion.

Both the Runtime backend and route materializer must consume that shared parser.
The materializer may project only the identity fields it needs, but it must not
maintain another complete Runtime-profile whitelist.

The rule is profile-driven. No branch may depend on RGB, colors, object order,
benchmark name, task ID, or a particular pair of cameras. Single-view profiles
remain supported through the same contract.

## Acceptance Criteria

- Single-view `sensor_ref` and multi-view `sensor_refs` profiles pass both consumers.
- Both fields, neither field, an empty set, duplicates, and unsupported refs fail
  closed with the same shared contract.
- The shipped profile passes the Runtime loader and materializer identity projection.
- The focused no-motion preparation path reaches route construction rather than
  failing at Runtime identity parsing.
- Frame, calibration, freshness, collision, IK, authorization, Gateway admission,
  and terminal settlement behavior are unchanged.
