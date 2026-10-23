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

from .visual_perception import LabArtifactStore, LabVisualPerception, RecordedGraspProvider


def build_visual_providers(config_path, engine, artifact_root, inference, *, segmentation=None, geometry_method=None):
    if config_path is None:
        raise ValueError("the lab Agent requires perception_config_path with segmentation, geometry recovery and GraspNet workers")
    config_path = Path(config_path).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    store = LabArtifactStore(artifact_root)
    variables = {**os.environ, "LAB_ARTIFACT_ROOT": str(store.root),
                 "LAB_CONFIG_DIR": str(config_path.parent)}
    segmentation = segmentation or WorkerSegmentationProvider(
        JsonlProcessWorkerClient(_worker_config(config["segmentation_worker"], variables, "segmentation_worker")),
        worker_artifact_root=store.root / "workers/sam2")
    method = geometry_method or config["geometry_method"]
    geometry = WorkerGeometryRecoveryProvider(
        JsonlProcessWorkerClient(_worker_config(config["geometry_workers"][method], variables, "geometry_worker")),
        worker_artifact_root=store.root / "workers/geometry")
    grasp = RecordedGraspProvider(GraspNetProposalProvider(
        JsonlProcessWorkerClient(_worker_config(config["grasp_worker"], variables, "grasp_worker")),
        artifact_store=store, **config["grasp"]), store)
    visual = LabVisualPerception(engine, LocalFilesystemArtifactResolver({"labutopia": store.root}), inference,
                                 segmentation=segmentation, geometry=geometry, store=store, grasps=grasp,
                                 provider_from_tcp=config["provider_from_tcp"])
    store.write("perception-configuration", {"profile": str(config_path), "configuration": config})
    return visual, grasp
