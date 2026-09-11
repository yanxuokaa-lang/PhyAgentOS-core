import asyncio
import os
import shlex
import sys
from unittest.mock import patch

import pytest

from PhyAgentOS.agent.tools.shell import ExecTool


@pytest.mark.skipif(os.name != "posix", reason="POSIX process-group cleanup")
@pytest.mark.parametrize("cancel", [False, True])
def test_shell_reaps_transport_on_timeout_and_cancel(cancel):
    async def exercise():
        created = asyncio.Event()
        processes = []
        spawn = asyncio.create_subprocess_shell

        async def capture(*args, **kwargs):
            process = await spawn(*args, **kwargs)
            processes.append(process)
            created.set()
            return process

        command = shlex.quote(sys.executable) + " -c " + shlex.quote("import time; time.sleep(30)")
        with patch("asyncio.create_subprocess_shell", capture):
            task = asyncio.create_task(ExecTool(timeout=0.1).execute(command))
            await created.wait()
            if cancel:
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await asyncio.wait_for(task, 3)
            else:
                assert "timed out" in await asyncio.wait_for(task, 3)
        process = processes[0]
        assert process.returncode is not None
        assert process.stdout.at_eof()
        assert process.stderr.at_eof()

    asyncio.run(exercise())
