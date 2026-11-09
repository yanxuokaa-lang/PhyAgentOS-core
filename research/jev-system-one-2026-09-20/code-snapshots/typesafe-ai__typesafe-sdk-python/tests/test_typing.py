import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).with_name("typing")


@pytest.mark.parametrize("path", sorted(FIXTURES.rglob("*.py")), ids=lambda path: str(path.relative_to(FIXTURES)))
def test_public_typing(path: Path) -> None:
    result = subprocess.run(  # noqa: S603 - Fixed interpreter and arguments; paths are repository-owned fixtures.
        [sys.executable, "-m", "pyrefly", "check", "--config", str(ROOT / "pyrefly.toml"), "--expectations", str(path)],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
