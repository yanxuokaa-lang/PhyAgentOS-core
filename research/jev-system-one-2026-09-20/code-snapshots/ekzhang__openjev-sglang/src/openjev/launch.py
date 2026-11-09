"""Small stdlib-only helpers usable by Modal's base Python environment."""

import os
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request


def watch_process(process, name: str, poll_interval: float = 1.0) -> threading.Event:
    """Exit this supervisor if its child dies; set the event before normal shutdown.

    A fatal child exit must terminate the process, not merely raise on a daemon
    thread. In Modal this lets the container runtime replace the failed server.
    """
    stopping = threading.Event()

    def watch():
        while not stopping.wait(poll_interval):
            code = process.poll()
            if code is not None and not stopping.is_set():
                print(
                    f"{name} exited unexpectedly (status {code}); exiting supervisor",
                    file=sys.stderr,
                    flush=True,
                )
                os._exit(1)

    threading.Thread(target=watch, name=f"{name}-watchdog", daemon=True).start()
    return stopping


def start_background(python: str, sglang_python: str, timeout: float = 1200):
    process = subprocess.Popen(
        [python, "-m", "openjev", "serve", "--host", "0.0.0.0", "--sglang-python", sglang_python],
        start_new_session=True,
    )
    deadline = time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"OpenJev exited with status {process.returncode}")
            try:
                with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=5) as response:
                    if response.status == 200:
                        process.openjev_stopping = watch_process(process, "OpenJev API")
                        return process
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(1)
        raise TimeoutError("OpenJev did not start before the startup deadline")
    except BaseException:
        stop_background(process)
        raise


def stop_background(process):
    if stopping := getattr(process, "openjev_stopping", None):
        stopping.set()
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=25)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
