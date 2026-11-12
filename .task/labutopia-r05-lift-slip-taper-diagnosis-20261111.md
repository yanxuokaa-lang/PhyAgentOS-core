# LabUtopia R05 lift slip: taper-band grasp diagnosis (run13/14/15)

Date: 2026-11-11. Tier C-Safety diagnostic; no code or scene change made.
Evidence: `out/labutopia-oracle-run13|14|15/` (HEAD `5d8667ae`, v17.6.12).

## Purpose

run13/14/15 all failed the R05 acquire lift identically (attach_err 0 -> 8.2 mm
in 0.42 s) across the swept drive cap (2/20 N) and retain (0.5/2 mm). The
previous session attributed the failure to a tilted (15-30 deg) grasp being
pulled off and proposed a presentation-order fix (flat grasps first). This
diagnosis re-checks that attribution against run artifacts.

## Corrections to the previous session's reading

1. Candidate numbering is depth-major: `bottle_grasp_candidates` loops
   `for fraction in depth_fractions: for tilt in tilts` (4 tilts x 8 depths =
   32 candidates), so `idx = depth_idx * 4 + tilt_idx`. Measured world-frame
   tilt per candidate (predictions approach_direction transformed by the
   calibration, dotted with the rim axis [0,0,1]) reproduces the nominal
   [0, 15, 30, 40] deg table exactly. The earlier tilt-major reading was wrong.
2. The agent-visible candidate order in all three runs IS already
   approach_dot-ascending (verified element-by-element), because the pour-gate
   rank primary key is `approach_dot` (= sin tilt) itself
   (`visual_perception.py` `_qualify_bottle_grasp`). The presentation layer is
   already flat-first; "乱序" was a misreading of depth-major indices.
3. All three runs selected candidate -16, whose measured tilt is 0.0 deg. The
   grasp was flat, not tilted. The "15 deg / -0.253" and "30 deg -16" claims
   were artifacts of the wrong numbering assumption.

Consequence: the previously ruled 方案 B (presentation-layer tilt-first
ordering) is a no-op — the order it asks for already exists. It was not
implemented.

## Measured failure mechanics (run15 phase-feedback)

- Close: fingers contact the sidewall at 19.76 mm per side; the target freezes
  at 19.26 mm (0.5 mm penetration); sustained contact impulse ~0.038-0.047 N*s
  per control step (~2.5 N normal force per finger); bilateral manifolds valid.
- Lift: TCP rises 8.3 mm while the bottle stays at its pose (dz ~0.06 mm,
  tilt 0.5 deg). Both fingers' contact impulse decays smoothly to exactly zero
  within ~0.2 s (about 1.4 mm of slide), while manifolds persist and the
  fingers creep toward the frozen target. attach_err then grows linearly to
  the 8 mm tolerance.

A smooth impulse decay to zero while sliding up means the surface recedes from
the pads: the grasp sits in a taper, and geometric recession - not insufficient
force - removes the normal force.

## R05 radius profile (same-capture object-point-cloud, world frame)

| z band (m) | median radius (mm) |
|---|---|
| 0.712-0.737 (lower body) | 23.6-30.4 (fat, roughly constant) |
| 0.757-0.767 (mid) | 20.5-23.8 |
| 0.787-0.807 (upper body) | 16.6 -> 14.1 (steep taper) |
| 0.812-0.827 (neck) | 14.0-16.1 (roughly constant) |

Candidate -16's grasp point is z=0.7697 — inside the taper transition
(~0.36 mm radius recession per mm of height, per side). Sliding 1.4 mm
exhausts the 0.5 mm penetration; retain 2 mm only extends this to ~2.8 mm;
the drive cap never binds because force comes from stiffness x frozen-target
penetration, not the cap. This explains why the entire cap/retain matrix was
ineffective.

## Why the equal-radius candidates were not chosen

- Depth idx 5/6 flat candidates (z ~0.733-0.748, fat equal-radius band) pass
  the geometric gates but die in the approach-feasibility probe — the same
  arm-vs-table collision family as v16.10.1 (link5 sphere r=63 mm vs table
  z=0.736). Depth idx 7 and one tilted variant are gate-rejected as "too close
  to the support end". Replay:
  `replay_task_affordance_funnel.py --artifacts out/labutopia-oracle-run15/artifacts/labutopia --entity R05`
  -> 32 evaluated, 28 geometry-qualified, 4 support-end rejects.
- Neck-band flat candidates (idx 0/4, z ~0.807-0.822, radius 14-16 mm
  roughly constant) are in the qualified 26, but the rank secondary keys
  (contact centering quality) put taper-band -16 first, and the agent selects
  the head of the list over opaque refs.

## Levers (not pulled; decision required)

1. Mechanism-level falsification run: command a neck-band candidate (0 or 4)
   through the existing acquire route without the agent loop, to verify that an
   equal-radius flat grasp holds through lift. Cheapest test of the physics
   claim; no code change.
2. Rank/gate equal-radius criterion (Adapter-private): make local radius
   uniformity (e.g. median |dr/dz| over +-10 mm around the grasp point) a rank
   key ahead of centering, or a gate reject for strong tapers. Contract
   unchanged; candidate set unchanged for option rank, reduced for gate.
3. Fixture change (v16.10.1's recorded lever): raise the reagent bottles so
   the fat band clears the arm-table collision envelope; needs user approval
   and a scene change.
- Rejected: slow lift (force decays geometrically; slower motion does not
  restore it) and the presentation-order fix (already implemented by the
  existing rank).

## Decision (2026-11-12)

The user ruled the control-policy direction: keep the contact force alive
with slow following, and tolerate in-process displacement rather than
freezing the grip dead. Implemented in v17.6.13 as a config-gated
`finger_hold_follow` re-freeze (finger target = measured − retain on every
held step, active in the close settle and all attached stages including
lift/carry; default off = legacy one-time freeze). This is the lever under
test for run16. Levers 1 (neck-candidate mechanism run) and 2 (equal-radius
rank key) stay as fallbacks if the drive cannot track the ~7 mm/s recession
rate within the 20 N cap — a quantity run15 artifacts cannot determine
ahead of time.

## Validation commands

See `.task/current.md` tail; nothing new required for this diagnostic.
