# LabUtopia delayed lift contact transient diagnosis

## Fresh reset and execution evidence

- No-motion reset workspace:
  `out/lab-fullchain-truth-20261103-v16_9_2-reset-no-motion-r1/`.
- Reset scene revision:
  `labutopia-tabletop-rod-rack-v1:f23ad48ac4ae4e328e4fc74ac652bf2e:0`.
- The reset task issued four Query/preparation records and no Action. R03 was at
  its support center near `[-0.270, -0.360, 0.752] m`; the RGB observation showed
  an open, empty gripper.
- Authorized execution workspace:
  `out/lab-fullchain-truth-20261103-v16_9_2-execute-r1/`.
- Task/revision:
  `task_448f4e2bf09042fe` / `revision_2544bf75668143b8`.
- The Action consumed the directly preceding qualified process/grasp opaque
  references and selected R03 candidate 57. It did not fall back to the raw
  GraspNet pool.
- R03 acquire phase feedback:
  `artifact://labutopia/phase-feedback/13269c76e3ad435ab37b3ac52f98bc97.json`.
- Phase video:
  `out/lab-fullchain-truth-20261103-v16_9_2-execute-r1/artifacts/labutopia/phase-video/189b4ac18c394dc3b5f16914548fa952.mp4`.

## Measured failure

Closure established bilateral selected-body load. The first seventeen retimed
lift samples remained load-valid. About 0.283 seconds after lift began, the
eighteenth lift sample reported:

- fresh manifolds for both fingers, with 15 substep samples per side;
- left/right interval impulse about `0.002397 / 0.0 N*s`;
- attachment error about `0.001690 m / 0.010160 rad`;
- `grasp_valid=false`, `contact_load_valid=false`;
- the object still classified as `on_support` by the execution outcome.

The v16.9.2 branch required `last_stage == "close"`. Retimed production routes
represent each control sample as a separate point, so only the first lift sample
sees `last_stage == "close"`; all later initial-lift samples see `"lift"`. The
single-interval grace therefore never ran for the measured transient, and the
Adapter returned `physical_grasp_lost`. Runtime correctly settled the subtask as
unknown with `world_change_started=true`, `outcome_known=false`, and
`possession_state=uncertain`. R04 and stirring did not start.

## Ownership and repair boundary

This remains an Isaac Adapter execution-evidence issue. AgentLoop and
Coordinator own task semantics, opaque selection, lifecycle, settlement and
recovery; Providers own candidate generation and qualification. None of those
layers should learn PhysX contact manifolds, USD paths or controller-cycle
state.

The repair persists a private `lift_grip_confirmed` fact after the successful
close-to-lift transition. A unilateral zero-load interval may consume the one
existing grace only while:

1. operation is acquire and stage is lift;
2. bilateral closure was confirmed before lift;
3. the measured object pose remains inside the existing
   `support_contact_allowed()` departure window;
4. both selected-body manifolds are fresh;
5. exactly one finger retains positive interval load;
6. existing attachment position and rotation limits pass.

The sample remains invalid evidence. The following interval must recover
bilateral positive load, and no second grace is available. Outside the support
window, during closure, for another operation, with missing/stale manifolds,
bilateral unloading or pose-limit failure, execution remains fail-closed.

## Validation and next motion boundary

Replacement-plant tests must use retimed `execution_steps`, because the
unretimed fixture keeps `last_stage` unchanged over a whole smooth segment and
would hide this production-only timing boundary. Tests cover delayed recovery,
support-window exclusion and all v16.9.2 failure cases.

The failed workspace must not be resumed. A new live run requires another
simulator reset, fresh scene revision, fresh perception and fresh preparation.
Regression success alone is not evidence of R03 retention, pouring, return,
R04 execution or stirring.
