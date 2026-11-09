"""Exercise fatal watchdog behavior in subprocesses, never inside pytest itself."""

import subprocess
import sys

import pytest


@pytest.mark.parametrize("child_code", [0, 7])
def test_child_exit_terminates_supervisor(child_code):
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            f"""
import subprocess, sys, time
from openjev.launch import watch_process
child = subprocess.Popen([sys.executable, '-c', 'import sys; sys.exit({child_code})'])
watch_process(child, 'test child', poll_interval=0.01)
time.sleep(10)
""",
        ],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 1
    assert f"status {child_code}" in result.stderr


def test_normal_shutdown_disarms_watchdog():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import subprocess, sys, time
from openjev.launch import watch_process
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)'])
stopping = watch_process(child, 'test child', poll_interval=0.01)
stopping.set()
child.terminate()
child.wait(timeout=3)
time.sleep(0.1)
""",
        ],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, result.stderr
