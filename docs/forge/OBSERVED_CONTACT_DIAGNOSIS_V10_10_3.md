# v10.10.3 Sensor attribution and observed-point collision design

## Finding

The user is correct that many practical single-view grasp pipelines collision-check
observed points instead of filling a whole object bounding box. Our current
`_pinch_geometry_diagnostics` checks whether the entire projected object box fits
between the fingers and whether its box overlaps the palm envelope. This is a
conservative whole-envelope condition, not a general local grasp collision test.
A large object can have a graspable local part; a box can overlap a palm where no
measured object surface exists. Fixing segmentation alone does not fix that model
mismatch. Existing rejection remains until a replacement receives equivalent
geometry, motion and failure-path validation.

Occlusion is different from missegmentation. A measured near-support point can
belong to the object, support, or a mixed depth boundary. Unobserved space behind
a surface is unknown. Neither should be silently relabeled by object height.
Absence of a point is not evidence that an entire volume is free, although a
point-based collision filter commonly checks only represented occupancy.

## GitHub source inspection

Read on 2026-09-20; references are pinned to the inspected repository revisions.
These are implementation mechanisms, not claims of robot safety certification.

| Project | Actual mechanism | Implication for PAOS |
| --- | --- | --- |
| [GraspNet baseline](https://github.com/graspnet/graspnet-baseline/blob/280c215129f759ed8649cb4e89fc5dfee55f4f80/utils/collision_detector.py) | `ModelFreeCollisionDetector` voxel-downsamples scene points, transforms them into each grasp frame, and counts points inside left/right finger, bottom and approach-sweep volumes. An optional inner-volume check detects empty grasps. | Local occupied volumes matter; entire object width is not required to fit. The fixed gripper constants and density thresholds are not automatically suitable for our Panda. |
| [GraspGen](https://github.com/NVlabs/GraspGen/blob/2dd8852e1be60f5f9d277fafcc621835cdf59110/grasp_gen/utils/point_cloud_utils.py) | `filter_colliding_grasps` samples gripper collision mesh surfaces and checks minimum distance to scene points. `depth_and_segmentation_to_point_clouds` separates object and scene points; its removal flag defaults false. | Observed scene occupancy is checked against embodiment geometry; sampling/threshold limitations remain. |
| [GraspGen demonstration](https://github.com/NVlabs/GraspGen/blob/2dd8852e1be60f5f9d277fafcc621835cdf59110/scripts/demo_collision_free_grasps.py) | Calls the above split with `remove_object_from_scene=True` for environment collision filtering. | Target contact and environment collision are separate concerns. This demo is not authority to ignore target collisions for all links or all motion phases. |
| [Contact-GraspNet](https://github.com/NVlabs/contact_graspnet/blob/721706067cc7f7889c32afe7b4f7955eb90bd866/contact_graspnet/contact_grasp_estimator.py) | Predicts from full or local scene regions; `filter_segment` retains predicted contacts close to the selected object segment. | Local contact attribution is separate from motion admission; this function does not itself establish complete-route collision safety. |
| [MoveIt 2](https://github.com/moveit/moveit2/blob/093360fef2ea8269c607821b551ffb2d4bc5c9a8/moveit_ros/perception/pointcloud_octomap_updater/src/pointcloud_octomap_updater.cpp) | Masks robot geometry, inserts observed endpoints as occupied cells and ray-traces free cells between the sensor and endpoints. | Observed occupied, observed free and unobserved space are distinct. This updater does not prove a particular planner's treatment of unknown cells. |

GraspGen local checkout HEAD matches the linked revision; tracked sources were
clean. Its extra untracked build directory was not used. GraspNet,
Contact-GraspNet and MoveIt files were fetched from GitHub, and branch revision
IDs were resolved through the GitHub API. No upstream code or new dependency was
copied into the production collision implementation.

## Frozen sensor measurements

New executable diagnostic: `examples/forge-adapters/robotwin20/scripts/diagnose_observed_contact.py`.
It reads saved RGB, masks, depth, calibration, clouds, observed support policy,
candidate transforms and already-persisted qualification. It does not import the
simulator or consume private actor geometry. No geometry, mask or task is mutated.

- Input build: `/home/yanxu/tmp/hephaestus/observed-prepare-4nb_bsh4`.
- Input qualification: `/home/yanxu/tmp/hephaestus/observed-readiness-qoxxzuyc`.
- Output: `/home/yanxu/tmp/hephaestus/observed-contact-diagnosis-3740n476`.
- `diagnosis.json`: exact command, timestamp, Git revision, diagnostic source text,
  input roots, observation identity, depth scale, neighborhood sizes, estimator
  policy and full per-variant measurements.
- `sensor-attribution.png`: original RGB, full object mask and near-support pixels.

The 523 object points and 70,606 support points reproduce mask/depth/calibration
pixel ordering within 5.96e-8 m and 1.19e-7 m respectively. This validates
correspondence, not absolute calibration accuracy. The depth scale is explicitly
0.001 m per stored unit. No point was subsampled or discarded for this diagnosis.

| Measurement | Result |
| --- | --- |
| Object/support mask intersection | 0 pixels |
| Object points within existing support median +/- 2 mm | 31 / 523 |
| Those near-plane points adjacent to a support inlier pixel | 22 / 31 |
| Points above that diagnostic band | 492 |
| Full world XY span | 69.684 x 86.014 mm |
| Above-band world XY span, diagnostic only | 52.604 x 50.593 mm |
| Near-band median RGB | [166, 251, 162] |
| Above-band median RGB | [1, 251, 1] |
| Support-inlier median RGB | [255, 255, 255] |

Boundary adjacency, support-height agreement and mixed RGB support further
segmentation investigation. They do not establish ownership or authorize deleting
31 points. RGB is descriptive, not a hard-coded green/white classifier.

Local analysis transforms all measured points into the calibrated hand frame.
It examines closing-axis width in X/Z neighborhoods around the canonical contact
center for 19 candidates x two arms x eight backoffs = 304 variants. These are
diagnostic windows, not replacement finger collision volumes.

| Neighborhood half-span in hand X/Z | Visible points | Closing width among nonempty windows | Empty windows |
| --- | --- | --- | --- |
| 5 mm | 0–77 | 0–49.153 mm | 62 / 304 |
| 10 mm | 0–202 | 0–88.839 mm | 34 / 304 |
| 20 mm | 10–456 | 19.082–90.054 mm | 0 / 304 |

Contact-center nearest-visible-point distance ranges from 0.559 to 21.924 mm.
A contact center can legitimately lie inside the object, rather than on a visible
surface; this distance is not a contact-validity verdict. Zero width can mean a
single visible point, not a safe narrow grasp. These results show why choosing a
small window solely to get a passing width would be invalid. Production should
use the actual finger/palm geometry, all relevant observed occupancy and phase-
specific contact rules rather than an arbitrary diagnostic window.

## Recommended implementation direction

1. **Environment occupancy:** transform observed scene depth into world-space
   points/voxels with calibrated uncertainty. Include support, other objects and
   unclassified visible occupancy; exclude robot self points using measured robot
   state. A semantic-label ambiguity must not remove an observed obstacle.
2. **Local target contact:** test actual finger and palm solids and approach swept
   volumes against the target's observed geometry. Distinguish the intended inner
   contact/closure region from forbidden finger-body or palm penetration. Whole-
   object AABBs may remain a broad-phase accelerator, not the final contact verdict.
3. **Unknown geometry:** preserve what is observed/free/unknown in evidence. Use
   the existing Runtime/profile boundary to state any unknown-space policy;
   unsupported critical clearance can request another observation through Agent
   recovery. Do not fill the whole AABB as measured matter or silently assert
   occluded space is known free.
4. **Transport attachment:** assess observed target geometry/uncertainty through
   lift, transport, descent and retreat. Passing a point-cloud contact filter is
   insufficient to change attachment or complete-route admission.
5. **A/B validation:** freeze observation, candidates, calibration, gripper and
   profile. Compare current envelope rejection against actual local geometry and
   whole-scene occupancy. Persist per-link/per-phase failures and sampling or voxel
   resolution. Retain known collision negative controls and run full readiness
   before proposing live execution.

This belongs in Adapter/readiness providers, using the existing observation and
candidate receipts. Core remains provider-neutral; Agent chooses evidence and
recovery, Runtime owns motion state and Gateway owns execution. No production
collision algorithm or threshold was changed in this diagnostic task.

## Seven-dimension diagnostic acceptance

| Dimension | Scope and result |
| --- | --- |
| Architecture integration | Diagnostic uses existing support estimator and grasp transforms. Production redesign remains proposed. |
| Recovery and idempotency | Unique output root, original task/masks/clouds unchanged, no retry or assignment. |
| Robotics safety | Zero Gateway calls, simulator imports/steps or motion; no removal or softened admission. |
| Context and performance | Measurements kept in artifacts; no LLM context/performance claim. |
| Configuration and reproducibility | Explicit inputs, scale, neighborhood spans and existing support policy; exact source saved. No learned checkpoint or random sampling used. |
| Maintainability and observability | Four regression tests cover pixel alignment, invalid-depth handling, image-edge adjacency, local frame rotation and empty neighborhoods. Ruff passes. |
| AgentLoop autonomy | No task-state or Tool behavior change. Live-model recovery and manipulation not exercised. |

Run with the existing RoboTwin interpreter for NumPy/Pillow, without launching
RoboTwin. Only adapter `src` is needed in PYTHONPATH:

```bash
PYTHONPATH=examples/forge-adapters/robotwin20/src \
/home/data/yanxu_migrated/miniconda3/envs/RoboTwin20/bin/python3.10 \
examples/forge-adapters/robotwin20/scripts/diagnose_observed_contact.py \
  --replay-root /home/yanxu/tmp/hephaestus/observed-prepare-4nb_bsh4 \
  --qualification-root /home/yanxu/tmp/hephaestus/observed-readiness-qoxxzuyc \
  --object-stem 53c74eec47f50241 --support-stem abc6a275756e51c7 \
  --depth-scale 0.001 --output-parent /home/yanxu/tmp/hephaestus
```

Tests: PAOS Python, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, adapter `src` and `scripts`
on PYTHONPATH, `-m pytest -q examples/forge-adapters/robotwin20/tests/test_observed_contact_diagnosis.py`.
Result: **4 passed**. Existing full suites were not rerun for this isolated
diagnostic addition. No new Skill/Node package, Runtime restart or execution video.
