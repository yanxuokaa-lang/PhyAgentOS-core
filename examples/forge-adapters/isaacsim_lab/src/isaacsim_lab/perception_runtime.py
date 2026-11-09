"""Lab deployment composition of reusable model Providers and their workers."""
from __future__ import annotations

import json
import os
from pathlib import Path

from PhyAgentOS.forge.artifacts import LocalFilesystemArtifactResolver
from robotwin20_adapter.geometry_recovery import WorkerGeometryRecoveryProvider
from robotwin20_adapter.grasp_proposal import GraspNetProposalProvider
from robotwin20_adapter.perception_profile import _worker_config
from robotwin20_adapter.process_worker import JsonlProcessWorkerClient
from robotwin20_adapter.single_view_perception import WorkerSegmentationProvider

from .oracle_grasp_geometry import OracleSimulatorTruthGraspProvider
from .simulator_truth_perception import load_truth_manifest
from .visual_perception import LabArtifactStore, LabVisualPerception, RecordedGraspProvider


def build_visual_providers(config_path, engine, artifact_root, inference, *, segmentation=None, geometry_method=None):
    if config_path is None:
        raise ValueError("the lab Agent requires perception_config_path with GraspNet and mode-specific perception settings")
    config_path = Path(config_path).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    store = LabArtifactStore(artifact_root)
    variables = {**os.environ, "LAB_ARTIFACT_ROOT": str(store.root),
                 "LAB_CONFIG_DIR": str(config_path.parent)}
    mode = config.get("perception_mode", "model")
    if mode not in {"model", "simulator_truth"}:
        raise ValueError("perception_mode must be model or simulator_truth")
    grasp_source = config.get("grasp_source", "graspnet_worker")
    if grasp_source not in {"graspnet_worker", "simulator_truth_oracle"}:
        raise ValueError("grasp_source must be graspnet_worker or simulator_truth_oracle")
    oracle_config = None
    if grasp_source == "simulator_truth_oracle":
        if mode != "simulator_truth":
            raise ValueError("simulator_truth_oracle grasp requires perception_mode simulator_truth")
        oracle_config = config.get("oracle_grasp")
        if not isinstance(oracle_config, dict):
            raise ValueError("simulator_truth_oracle requires an oracle_grasp configuration block")
    if mode == "simulator_truth":
        manifest_path = config.get("simulation_truth_manifest_path")
        if not manifest_path:
            raise ValueError("simulator_truth perception requires simulation_truth_manifest_path")
        manifest_path = Path(manifest_path)
        if not manifest_path.is_absolute():
            manifest_path = (config_path.parent / manifest_path).resolve()
        truth_manifest = load_truth_manifest(manifest_path)
        segmentation = geometry = None
    else:
        truth_manifest = None
        segmentation = segmentation or WorkerSegmentationProvider(
            JsonlProcessWorkerClient(_worker_config(config["segmentation_worker"], variables, "segmentation_worker")),
            worker_artifact_root=store.root / "workers/sam2")
        method = geometry_method or config["geometry_method"]
        geometry = WorkerGeometryRecoveryProvider(
            JsonlProcessWorkerClient(_worker_config(config["geometry_workers"][method], variables, "geometry_worker")),
            worker_artifact_root=store.root / "workers/geometry")
    if grasp_source == "simulator_truth_oracle":
        base_xy = oracle_config.get("approach_base_xy_m", (0., 0.))
        if (not isinstance(base_xy, (list, tuple)) or len(base_xy) != 2
                or any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in base_xy)):
            raise ValueError("oracle approach_base_xy_m must be a numeric 2-vector")
        oracle = OracleSimulatorTruthGraspProvider(
            store, gripper_geometry=oracle_config, base_xy=tuple(float(value) for value in base_xy),
            bottle_depth_fractions=oracle_config.get("bottle_depth_fractions"))
        grasp = RecordedGraspProvider(oracle, store)
    else:
        grasp = RecordedGraspProvider(GraspNetProposalProvider(
            JsonlProcessWorkerClient(_worker_config(config["grasp_worker"], variables, "grasp_worker")),
            artifact_store=store, **config["grasp"]), store)
    visual = LabVisualPerception(engine, LocalFilesystemArtifactResolver({"labutopia": store.root}), inference,
                                 segmentation=segmentation, geometry=geometry, store=store, grasps=grasp,
                                 provider_from_tcp=config["provider_from_tcp"], truth_manifest=truth_manifest)
    if grasp_source == "simulator_truth_oracle":
        oracle.bind_records(lambda calibration_ref: visual.observations.get(calibration_ref, {}))
    store.write("perception-configuration", {"profile": str(config_path), "configuration": config,
                                               "perception_mode": mode, "grasp_source": grasp_source})
    return visual, grasp
