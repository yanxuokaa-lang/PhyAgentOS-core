import asyncio
import base64
import importlib.util
import io
import threading
import time
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from test_agent_foundation import setup_task

from PhyAgentOS.forge.binding import ForgeSkillBindingResolver
from PhyAgentOS.forge.task import ToolExecutionRecord
from PhyAgentOS.forge.tool_client import ForgeToolClient
from PhyAgentOS.skill_runtime.integration import ActiveRuntimeRegistry, DynamicRuntimeSet


def test_query_timeout_reaches_http_without_changing_discovery_or_action():
    async def exercise():
        requests = []

        def respond(request):
            requests.append(request)
            return httpx.Response(202 if request.url.path.endswith('/invocations') else 200,
                                  json={'ok': True, 'data': {}})

        async with ForgeToolClient('http://test', transport=httpx.MockTransport(respond)) as client:
            await client.invoke_query('scene', 'understand', {}, timeout_ms=300000)
            await client.list_tools()
            await client.invoke_query('scene', 'observe', {})
        assert requests[0].extensions['timeout'] == {
            'connect': 10.0, 'read': 300.0, 'write': 10.0, 'pool': 10.0}
        assert requests[1].extensions['timeout']['read'] == 10.0
        assert requests[2].extensions['timeout']['read'] == 10.0
    asyncio.run(exercise())


def test_slow_query_completes_with_explicit_http_read_timeout():
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers['Content-Length']))
            time.sleep(0.25)
            body = b'{"ok":true,"data":{"status":"available"}}'
            self.send_response(200)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        async def exercise():
            async with ForgeToolClient(f'http://127.0.0.1:{server.server_port}', timeout_s=0.1) as client:
                result = await client.invoke_query('scene', 'understand', timeout_ms=1000)
                assert result['data']['status'] == 'available'
        asyncio.run(exercise())
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize('runtime_state', ['absent', 'different', 'same'])
def test_recovery_registers_only_owning_runtime(tmp_path, runtime_state):
    coordinator, task = setup_task(tmp_path)
    binding = task.primary_skill_binding
    runtime = None if runtime_state == 'absent' else SimpleNamespace(
        runtime_instance_id=binding.runtime_instance_id if runtime_state == 'same' else 'replacement',
        gateway_url=binding.gateway_url, skill_name=binding.skill_name,
        skill_version=binding.skill_version, profile=binding.runtime_profile,
        gateway_identity=binding.gateway_identity, task_binding_ids=set(),
    )
    registry = ActiveRuntimeRegistry(runtime)
    coordinator.binding_resolver = ForgeSkillBindingResolver(registry)
    coordinator.runtime_task_binding_ids = DynamicRuntimeSet(registry, 'task_binding_ids')
    before = coordinator.get_task(task.task_id).model_dump(mode='json')
    result = asyncio.run(coordinator.reconcile_nonterminal())
    assert result.model_dump(mode='json') == before
    if runtime is not None:
        assert runtime.task_binding_ids == ({binding.binding_id} if runtime_state == 'same' else set())


@pytest.mark.parametrize('runtime_state', ['absent', 'different'])
def test_recovery_does_not_query_invocation_through_nonowning_runtime(
    tmp_path, runtime_state
):
    coordinator, task = setup_task(tmp_path)
    binding = task.primary_skill_binding
    runtime = None if runtime_state == 'absent' else SimpleNamespace(
        runtime_instance_id='replacement',
        gateway_url=binding.gateway_url,
        skill_name=binding.skill_name,
        skill_version=binding.skill_version,
        profile=binding.runtime_profile,
        gateway_identity=binding.gateway_identity,
        task_binding_ids=set(),
    )
    registry = ActiveRuntimeRegistry(runtime)
    coordinator.binding_resolver = ForgeSkillBindingResolver(registry)
    coordinator.runtime_task_binding_ids = DynamicRuntimeSet(registry, 'task_binding_ids')
    coordinator.client = SimpleNamespace(
        invocation_status=AsyncMock(side_effect=AssertionError('wrong Runtime status read')),
        invocation_result=AsyncMock(side_effect=AssertionError('wrong Runtime result read')),
    )

    def add_running_action(current):
        current.active_revision.execution_records.append(ToolExecutionRecord(
            record_id='action-record-1',
            revision_id=current.active_revision_id,
            tool_id='object.place',
            semantics='action',
            caller_id='paos:test',
            status='running',
            invocation_id='invocation://object-place/original',
        ))

    coordinator.store.update(
        task.task_id, add_running_action, event_type='test_running_action'
    )
    before = coordinator.get_task(task.task_id).model_dump(mode='json')
    result = asyncio.run(coordinator.reconcile_nonterminal())

    assert result.model_dump(mode='json') == before
    coordinator.client.invocation_status.assert_not_awaited()
    coordinator.client.invocation_result.assert_not_awaited()
    if runtime is not None:
        assert runtime.task_binding_ids == set()


def test_node_archive_includes_materializer_and_runtime_dependencies():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('node_builder', root / 'scripts/build_robotwin20_node.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    payload = builder._source_archive(root / 'examples/forge-adapters/robotwin20',
                                      root / 'examples/forge-skills/pick-place-workflow')
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(payload))) as archive:
        assert 'adapter/scripts/materialize_complete_route.py' in archive.namelist()
        assert 'adapter/runtime/robotwin_persistent_worker.py' in archive.namelist()
        assert not any('__pycache__' in name for name in archive.namelist())


def test_repeated_cancel_releases_terminal_task_binding(tmp_path):
    coordinator, task = setup_task(tmp_path)
    asyncio.run(coordinator.cancel_task(task.task_id, reason='first cancellation without runtime'))
    references = {task.primary_skill_binding.binding_id}
    coordinator.runtime_task_binding_ids = references
    result = asyncio.run(coordinator.cancel_task(task.task_id, reason='repair ownership'))
    assert result.terminal
    assert references == set()
