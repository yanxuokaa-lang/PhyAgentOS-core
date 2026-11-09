"""Local launcher for self-contained probes in an existing Modal container."""

import base64
import json
import subprocess
import zlib


def run_remote(script, container, payload, output, *, total, progress_every):
    packed = base64.b64encode(zlib.compress(json.dumps(payload).encode())).decode()
    command = [
        "uv",
        "run",
        "modal",
        "container",
        "exec",
        "--no-pty",
        container,
        "--",
        "/opt/openjev/.venv/bin/python",
        "-c",
        script.read_text(),
        "--remote",
        packed,
    ]
    predictions, timings = [], []
    log_path = output / "remote.log"
    with (
        log_path.open("w") as log,
        subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        ) as process,
    ):
        for line in process.stdout:
            log.write(line)
            log.flush()
            if "RESULT_JSON " in line:
                predictions.append(json.loads(line.split("RESULT_JSON ", 1)[1]))
                if len(predictions) % progress_every == 0:
                    print(f"Completed {len(predictions)}/{total}", flush=True)
            elif "TIMING_JSON " in line:
                timings.append(json.loads(line.split("TIMING_JSON ", 1)[1]))
                print(line.strip(), flush=True)
        if process.wait():
            raise RuntimeError(f"Remote probe failed; see {log_path}")
    return predictions, timings
