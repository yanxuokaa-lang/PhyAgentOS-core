# Transparent geometry worker

This worker composes the actual ReMake or DFNet model with the existing PAOS JSONL process transport. It returns aligned metre-valued depth and model provenance. It does not generate grasps, select objects, qualify motion, or own task state. GraspNet remains a separate Provider.

The laboratory deployment is configured in `../../isaacsim_lab/configs/labutopia-mixture-perception.json`. `geometry_method` selects one of the `geometry_workers`; Python, source, weights, device, image dimensions, depth range and seed are explicit. The supplied profile uses a 0–3 m input range for the original third-person view. This is a diagnostic range, not evidence that either model generalizes to that distance.

## Sources and runtime

Official sources:

- ReMake: https://github.com/ChengYaofeng/ReMake (tested source `4f568148c8421544136bf49bb941149e0c990a34`). Its README links the released checkpoint.
- DFNet: https://github.com/Galaxies99/TransCG. Its README links Google Drive and Baidu releases.
- Relative depth: https://huggingface.co/depth-anything/Depth-Anything-V2-Small; file `depth_anything_v2_vits.pth`.

Keep sources/weights outside PAOS. The tested local setup uses `~/.cache/paos/transparent_geometry/{ReMake,TransCG,checkpoints,runtime}`, with `remake.tar`, `dfnet.tar` and the relative checkpoint under `checkpoints`. ReMake and the relative checkpoint were downloaded and loaded; the official DFNet download hit its quota and no DFNet model result is claimed.

Apply the PAOS-owned import patch to the dedicated ReMake checkout:

```bash
git -C "$HOME/.cache/paos/transparent_geometry/ReMake" apply \
  "$PWD/examples/forge-adapters/robotwin20/patches/remake-inference-import.patch"
```

The patch removes one unused visualization import that pulled in Open3D. It changes no model math. The worker records both source Git revision and local modified filenames.

The tested interpreter inherits the existing segmentation environment's Torch 2.11.0+cu128 and NumPy 2.2.6. Required inference packages are torch, torchvision, numpy, Pillow, opencv-python, timm, einops, scipy and matplotlib. The independent worker prevents their imports from entering PAOS/Isaac's interpreters. `gdown` is only for acquiring official weights; `pytest` is only for the parity check. Do not substitute an untrained checkpoint when loading fails.

ReMake uses the released `vits` relative model, 640×480 input, cubic relative-branch resize, the upstream channel swap, depth normalization 1, and nearest-neighbor restoration to the capture size. DFNet uses 320×240, upstream outlier removal/inpainting and depth normalization. Worker replies record preprocessing. Float output, original dimensions, metre units and finite target values are checked; those checks establish usable output format, not physical accuracy.

## Reproduce the original-scene queries

From the PAOS root, each command requires a new output directory:

```bash
export PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src
.venv/bin/python -m isaacsim_lab.perception_probe \
  --profile examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture.json \
  --replay out/releases/v15.9.0/tabletop-perception-20261023-r2 \
  --geometry-method remake \
  --workspace "out/releases/v16.0.0/replay-$(date +%Y%m%d-%H%M%S)"
```

`--replay` uses the recorded RGB-D/calibration, visual claims and SAM2 masks. ReMake and GraspNet execute anew; the probe does not construct an Isaac engine or connect visual entities to simulator bodies. `--geometry-method dfnet` selects the other mechanism, provided its trained weights are available. `--perception-config` allows a separate deployment configuration.

Omitting `--replay` captures the original configured scene and runs VLM/SAM2 too. `--sensor-ref sensor://tabletop_wrist` reads the existing wrist camera at its current pose; it does not move the arm into a useful view. The current pose is substantially occluded by the robot. These commands issue no motion.

Outputs include `perception.json`, raw capture artifacts, model masks, recovered depth, recovery metadata, Nx3 clouds with JSON lineage sidecars, explicit feature estimates/failures and actual GraspNet requests/predictions. A point-cloud sidecar links raw depth, recovered depth and model metadata through `geometry_ref`; public artifacts retain their capture references. Unknown geometry confidence is not manufactured from the fraction of nonzero depth. Point-cloud-only grasp queries are supported by the public endpoint and Agent projection.

## Validation

```bash
PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src \
.venv/bin/pytest -q \
  examples/forge-adapters/robotwin20/tests/test_geometry_recovery.py \
  examples/forge-adapters/robotwin20/tests/test_geometry_worker.py \
  examples/forge-adapters/isaacsim_lab/tests/test_visual_perception.py \
  examples/forge-adapters/isaacsim_lab/tests/test_perception_probe.py \
  tests/test_planning_projection.py
```

For numerical parity, run the optional test in the geometry interpreter with the actual weights and original replay:

```bash
PAOS_GEOMETRY_CACHE="$HOME/.cache/paos/transparent_geometry" \
PAOS_GEOMETRY_REPLAY="$PWD/out/releases/v15.9.0/tabletop-perception-20261023-r2" \
PAOS_GEOMETRY_PARITY_OUTPUT="$PWD/out/releases/v16.0.0/parity-$(date +%Y%m%d-%H%M%S).json" \
  "$HOME/.cache/paos/transparent_geometry/runtime/bin/python" -m pytest -q \
  examples/forge-adapters/robotwin20/tests/test_geometry_upstream.py
```

The test executes the upstream preprocessing/inference method bodies with the same trained models; it does not import the upstream training/UI dependencies. The recorded CPU comparison had maximum absolute difference 0 m. This proves arithmetic compatibility for that input, not scene accuracy. The ordinary unit suite skips this external-weight test explicitly. Seed, versions, original capture and configuration remain necessary to compare reruns; GPU kernels and changed model/software versions can affect output.

## Preparation boundary

Current workers always return `unverified_estimate`. The third-person experiment had significant displacement; both tested views had unresolved reagent labels and process features. No spatial envelope with invented numeric confidence is emitted. Consequently the semantic process-binding/preparation chain remains unavailable until validated object geometry is supplied. There is no configuration switch to promote these estimates to executable observations.

Process feature fitting requires explicit visible rim/endpoint support. A label edge is not a rim and an occlusion boundary is not a rod endpoint. Physics correspondence occurs only at capability/preparation time, preserves perception IDs, and reads recovered camera points. It never repairs geometry or overwrites a GraspNet pose. Runtime/Coordinator continue to own acquisition, possession, cancellation, recovery and settlement. All live execution acceptance remains open.
