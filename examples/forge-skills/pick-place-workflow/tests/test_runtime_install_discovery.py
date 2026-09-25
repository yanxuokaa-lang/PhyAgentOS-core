import json
import re
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml
from PhyAgentOS.skill_runtime.catalog import SkillCatalog
from PhyAgentOS.skill_runtime.installer import SkillInstaller
from PhyAgentOS.skill_runtime.integration import discover_active_runtime
from PhyAgentOS.skill_runtime.manager import RuntimeManager, RuntimeStatusReport
from PhyAgentOS.skill_runtime.manifest import load_manifest
from PhyAgentOS.skill_runtime.state import RuntimeState, RuntimeStateStore

BUNDLE_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TOOLS = {
    "scene.observe",
    "manipulation.capabilities",
    "scene.understand",
    "scene.bind",
    "task.goal",
    "manipulation.target",
    "grasp.propose",
    "manipulation.prepare",
    "object.acquire",
    "object.place",
}


def _package_bundle(tmp_path: Path) -> Path:
    output = tmp_path / "dist"
    command = [
        sys.executable,
        str(Path(__file__).resolve().parents[4] / "scripts" / "package_skill.py"),
        str(BUNDLE_ROOT),
        "--output-dir",
        str(output),
        "--force",
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    version = load_manifest(BUNDLE_ROOT / "skill.yaml").version
    archive = output / f"pick-place-workflow-{version}.tar.gz"
    assert archive.is_file(), completed.stdout
    return archive


def test_manifest_v2_bundle_installs_and_catalog_reloads_required_tools(tmp_path):
    archive = _package_bundle(tmp_path)
    state_store = RuntimeStateStore(tmp_path / "run")
    installer = SkillInstaller(tmp_path / "skills", state_store=state_store)

    manifest = installer.install(archive)
    reloaded = SkillCatalog(tmp_path / "skills").get("pick-place-workflow")

    assert manifest == reloaded
    assert manifest.name == "pick-place-workflow"
    assert manifest.manifest_version == 2
    assert set(manifest.required_tools) == EXPECTED_TOOLS
    assert manifest.profiles["fake"].dataflow.as_posix() == "profiles/fake/dataflow.yaml"
    assert manifest.profiles["robotwin-blocks-ranking-observed"].environment == {
        "ROBOTWIN20_ROUTE_GEOMETRY_SOURCE": "observed",
        "ROBOTWIN20_SIMULATION_ACTION_MODE": "disabled",
        "ROBOTWIN20_GOAL_SOURCE": "observation_owned",
    }
    assert manifest.profiles["robotwin-blocks-ranking-oracle"].environment == {
        "ROBOTWIN20_ROUTE_GEOMETRY_SOURCE": "oracle",
        "ROBOTWIN20_SIMULATION_ACTION_MODE": "runtime_monitored",
        "ROBOTWIN20_GOAL_SOURCE": "benchmark_task_definition",
    }
    assert manifest.profiles["robotwin-blocks-ranking-graspgen"].environment == {
        "ROBOTWIN20_ROUTE_GEOMETRY_SOURCE": "observed",
        "ROBOTWIN20_SIMULATION_ACTION_MODE": "runtime_monitored",
        "ROBOTWIN20_GOAL_SOURCE": "benchmark_task_definition",
    }
    assert (tmp_path / "skills" / "pick-place-workflow" / "SKILL.md").is_file()


def test_robotwin_dataflow_forwards_profile_owned_route_geometry_source():
    root = Path(__file__).parents[1]
    dataflow = yaml.safe_load(
        (root / "profiles/robotwin-persistent/dataflow.yaml").read_text(encoding="utf-8")
    )

    assert dataflow["nodes"][0]["env"]["ROBOTWIN20_ROUTE_GEOMETRY_SOURCE"] == (
        "${ROBOTWIN20_ROUTE_GEOMETRY_SOURCE}"
    )
    assert dataflow["nodes"][0]["env"]["ROBOTWIN20_SIMULATION_ACTION_MODE"] == (
        "${ROBOTWIN20_SIMULATION_ACTION_MODE}"
    )
    assert dataflow["nodes"][0]["env"]["ROBOTWIN20_GOAL_SOURCE"] == (
        "${ROBOTWIN20_GOAL_SOURCE}"
    )
    assert dataflow["nodes"][0]["env"]["ROBOTWIN20_MODEL"] == "${ROBOTWIN20_MODEL}"
    assert dataflow["nodes"][0]["env"]["ROBOTWIN20_REASONING_EFFORT"] == (
        "${ROBOTWIN20_REASONING_EFFORT}"
    )


def test_generic_robotwin_dataflow_uses_graspnet_without_graspgen_inputs():
    root = Path(__file__).parents[1]
    generic = (root / "profiles/robotwin-persistent/dataflow.yaml").read_text(encoding="utf-8")
    explicit_graspgen = (root / "profiles/robotwin-persistent/dataflow-graspgen.yaml").read_text(encoding="utf-8")
    assert "GRASPNET_PYTHON" in generic
    assert "GRASPNET_DEVICE" in generic
    assert "GRASPGEN_" not in generic
    assert "GRASPGEN_PYTHON" in explicit_graspgen
    assert "GRASPNET_" not in explicit_graspgen


def test_generic_materializer_closure_is_graspnet_owned():
    adapter_profiles = Path(__file__).parents[3] / "forge-adapters/robotwin20/profiles/robotwin20"
    materializer = yaml.safe_load(
        (adapter_profiles / "persistent-materializer.yaml").read_text(encoding="utf-8")
    )
    graspgen_materializer = yaml.safe_load(
        (adapter_profiles / "persistent-materializer-graspgen.yaml").read_text(encoding="utf-8")
    )
    assert materializer["route-input-profile"].endswith("route-inputs-graspnet.yaml")
    assert materializer["grasp-transform-attestation"].endswith("graspnet-tool-transform.json")
    assert "GRASPNET_SOURCE_ROOT" in materializer["grasp-provider-source-root"]
    assert "GRASPGEN_SOURCE_ROOT" in graspgen_materializer["grasp-provider-source-root"]


def test_robotwin_profile_declares_every_external_environment_used_by_dataflow():
    manifest = load_manifest(BUNDLE_ROOT / "skill.yaml")
    profile = manifest.profiles["robotwin-persistent"]
    dataflow = (BUNDLE_ROOT / profile.dataflow).read_text(encoding="utf-8")
    placeholders = set(re.findall(r"\$\{([A-Z][A-Z0-9_]*)\}", dataflow))
    installer_owned = {"FORGE_RUNTIME_BIN", "PAOS_SKILL_ROOT", "PAOS_SKILL_NAME", "PAOS_SKILL_VERSION"}
    assert set(profile.required_environment) == placeholders - installer_owned
    assert "PAOS_ROBOTWIN20_ADAPTER_ROOT" not in placeholders
    assert "PAOS_ROBOTWIN20_ADAPTER_ROOT" not in profile.required_environment


def test_robotwin_environment_template_tracks_non_secret_required_inputs():
    manifest = load_manifest(BUNDLE_ROOT / "skill.yaml")
    profile = manifest.profiles["robotwin-persistent"]
    template = (
        BUNDLE_ROOT
        / "profiles"
        / "robotwin-persistent"
        / "runtime.env.example"
    ).read_text(encoding="utf-8")
    template_names = {
        line.partition("=")[0].strip()
        for line in template.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert template_names == set(profile.required_environment) - {
        "ROBOTWIN20_MODEL_API_KEY",
        *profile.environment,
    }


def test_prepare_contract_requires_verbatim_capability_arm_ids():
    contract = yaml.safe_load(
        (BUNDLE_ROOT / "contracts/manipulation.prepare.tool.yaml").read_text(encoding="utf-8")
    )
    description = contract["input_schema"]["properties"]["intent"]["properties"]["allowed_arms"]["description"]
    assert "manipulation.capabilities" in description
    assert "verbatim" in description
    assert "left_arm" in description
    skill_text = (BUNDLE_ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "opaque Runtime resource" in skill_text
    assert "left_arm`/`right_arm" in skill_text


def test_grasp_contract_requires_verbatim_entity_identity():
    contract = yaml.safe_load(
        (BUNDLE_ROOT / "contracts/grasp.propose.tool.yaml").read_text(encoding="utf-8")
    )
    description = contract["input_schema"]["properties"]["targets"]["items"]["properties"]["entity_ref"]["description"]
    assert "verbatim" in description
    assert "color" in description
    skill_text = (BUNDLE_ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "color-derived alias" in skill_text


class HealthyRuntimeManager:
    def __init__(self, state, manifest):
        self.state = state
        self.manifest = manifest
        self.calls = []

    def status(self, skill_name):
        self.calls.append(skill_name)
        return RuntimeStatusReport(
            state=self.state if skill_name == self.manifest.name else None,
            flow_running=True,
            gateway_ready=True,
            tool_contexts={tool_id: True for tool_id in self.manifest.required_tools},
        )


def test_discovery_publishes_only_one_healthy_installed_runtime(tmp_path):
    archive = _package_bundle(tmp_path)
    state_store = RuntimeStateStore(tmp_path / "run")
    SkillInstaller(tmp_path / "skills", state_store=state_store).install(archive)
    catalog = SkillCatalog(tmp_path / "skills")
    manifest = catalog.get("pick-place-workflow")
    state = RuntimeState(
        skill_name=manifest.name,
        profile="fake",
        status="running",
        flow_name="paos-pick-place-workflow-fake",
        gateway_url=manifest.gateway_url,
        gateway_identity="gateway_fake_fixture",
    )
    state_store.save(state)
    manager = HealthyRuntimeManager(state, manifest)

    active = discover_active_runtime(
        catalog=catalog,
        state_store=state_store,
        manager=manager,
    )

    assert active is not None
    assert active.skill_name == "pick-place-workflow"
    assert active.skill_version == manifest.version
    assert active.profile == "fake"
    assert active.gateway_identity == "gateway_fake_fixture"
    assert manager.calls == ["pick-place-workflow"]


def test_discovery_fail_closed_for_non_ready_runtime(tmp_path):
    archive = _package_bundle(tmp_path)
    state_store = RuntimeStateStore(tmp_path / "run")
    SkillInstaller(tmp_path / "skills", state_store=state_store).install(archive)
    catalog = SkillCatalog(tmp_path / "skills")
    manifest = catalog.get("pick-place-workflow")
    state = RuntimeState(
        skill_name=manifest.name,
        profile="fake",
        status="starting",
        flow_name="paos-pick-place-workflow-fake",
        gateway_url=manifest.gateway_url,
    )
    state_store.save(state)

    class NotReadyManager:
        def status(self, skill_name):
            return RuntimeStatusReport(
                state=state,
                flow_running=False,
                gateway_ready=False,
                tool_contexts={tool_id: False for tool_id in manifest.required_tools},
            )

    assert discover_active_runtime(
        catalog=catalog,
        state_store=state_store,
        manager=NotReadyManager(),
    ) is None


def test_runtime_manager_status_reads_http_health_and_fails_closed_on_missing_context(tmp_path):
    requests = []
    missing_tool = "object.place"

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            requests.append(self.path)
            if self.path == "/tools":
                payload = {"ok": True, "data": {"gateway_identity": "gateway-http"}}
            elif self.path.endswith("/context"):
                tool_id = self.path[len("/tools/") : -len("/context")]
                payload = {
                    "ok": True,
                    "data": {
                        "ready": tool_id != missing_tool,
                        "binding_error": None if tool_id != missing_tool else "provider unavailable",
                    },
                }
            else:
                self.send_response(404)
                self.end_headers()
                return
            body = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):  # noqa: A002
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        archive = _package_bundle(tmp_path)
        state_store = RuntimeStateStore(tmp_path / "run")
        SkillInstaller(tmp_path / "skills", state_store=state_store).install(archive)
        catalog = SkillCatalog(tmp_path / "skills")
        manifest = catalog.get("pick-place-workflow")
        object.__setattr__(manifest, "gateway_url", f"http://127.0.0.1:{server.server_port}")

        class LocalCatalog:
            def get(self, skill_name):
                assert skill_name == manifest.name
                return manifest

        state = RuntimeState(
            skill_name=manifest.name,
            profile="fake",
            status="running",
            flow_name="paos-pick-place-workflow-fake",
            gateway_url=manifest.gateway_url,
        )
        state_store.save(state)
        manager = RuntimeManager(
            catalog=LocalCatalog(), state_store=state_store, poll_interval_s=0.01
        )
        manager._flow_running = lambda flow_name: True

        report = manager.status(manifest.name)
        assert report.gateway_ready is True
        assert report.tool_contexts[missing_tool] is False
        assert report.state is not None
        assert report.state.status == "failed"
        assert "Tool context is not ready" in (report.state.last_error or "")
        assert f"/tools/{missing_tool}/context" in requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_graspnet_acceptance_profile_preserves_observed_action_boundaries():
    manifest = load_manifest(BUNDLE_ROOT / "skill.yaml")
    profile = manifest.profiles["robotwin-blocks-ranking-graspnet"]
    assert profile.environment == {
        "ROBOTWIN20_ROUTE_GEOMETRY_SOURCE": "observed",
        "ROBOTWIN20_SIMULATION_ACTION_MODE": "runtime_monitored",
        "ROBOTWIN20_GOAL_SOURCE": "benchmark_task_definition",
    }
    assert profile.dataflow == manifest.profiles["robotwin-blocks-ranking-observed"].dataflow
    assert "GRASPNET_CHECKPOINT" in profile.required_environment
    assert not any(name.startswith("GRASPGEN_") for name in profile.required_environment)
    adapter = BUNDLE_ROOT.parents[1] / "forge-adapters/robotwin20"
    grasp = yaml.safe_load((adapter / "profiles/robotwin20/graspnet.yaml").read_text())
    assert grasp["sample_count"] == 128
    assert grasp["max_candidates"] == 32
    assert grasp["apply_nms"] is True
