"""Smoke-test wheel and sdist installations."""

# ruff: noqa: INP001, S603, S607 - Standalone helper using explicit uv arguments.

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def check_distributions(distributions: Path, version: str) -> None:
    """Check both distributions in isolated environments."""
    wheels, sdists = list(distributions.glob("*.whl")), list(distributions.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise ValueError("Expected exactly one wheel and one source distribution")
    with tempfile.TemporaryDirectory(prefix="system-one-adapter-distributions-") as temporary:
        consumer = Path(temporary)
        installation_check = consumer / "check_installed_distribution.py"
        shutil.copyfile(Path(__file__).with_name("check_installed_distribution.py"), installation_check)
        subprocess.run(
            ["uv", "build", "--wheel", str(sdists[0].resolve()), "--out-dir", str(consumer / "rebuilt")],
            cwd=consumer,
            check=True,
        )
        rebuilt = list((consumer / "rebuilt").glob("*.whl"))
        if len(rebuilt) != 1:
            raise ValueError("Expected one wheel rebuilt from the source distribution")
        for wheel in [wheels[0].resolve(), rebuilt[0]]:
            subprocess.run(
                [
                    "uv",
                    "run",
                    "--isolated",
                    "--no-project",
                    "--python",
                    sys.executable,
                    "--with",
                    str(wheel),
                    "python",
                    str(installation_check),
                    version,
                ],
                cwd=consumer,
                check=True,
            )


if __name__ == "__main__":
    check_distributions(Path(sys.argv[1]), sys.argv[2])
