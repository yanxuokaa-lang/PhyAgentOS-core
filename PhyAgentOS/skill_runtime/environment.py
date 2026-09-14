"""Operator-owned environment input for managed Skill runtimes."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path

_ENVIRONMENT_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class RuntimeEnvironmentFileError(ValueError):
    """Raised when a Runtime environment file cannot be loaded safely."""


def load_runtime_environment_file(path: str | Path) -> dict[str, str]:
    """Parse a non-executing ``KEY=VALUE`` Runtime environment file."""

    source = Path(path).expanduser()
    try:
        content = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise RuntimeEnvironmentFileError(
            f"Runtime environment file cannot be read: {source}"
        ) from exc

    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        name, separator, raw_value = line.partition("=")
        name = name.strip()
        if not separator or not _ENVIRONMENT_NAME.fullmatch(name):
            raise RuntimeEnvironmentFileError(
                f"Invalid Runtime environment entry at {source}:{line_number}; "
                "expected KEY=VALUE"
            )
        if name in values:
            raise RuntimeEnvironmentFileError(
                f"Duplicate Runtime environment key {name!r} at {source}:{line_number}"
            )
        value = raw_value.strip()
        if value[:1] in {'"', "'"}:
            if len(value) < 2 or value[-1] != value[0]:
                raise RuntimeEnvironmentFileError(
                    f"Unterminated quoted value for {name!r} at {source}:{line_number}"
                )
            value = value[1:-1]
        values[name] = value
    return values


def compose_runtime_environment(
    profile_environment: Mapping[str, str],
    *,
    env_file: str | Path | None = None,
    process_environment: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build one launch environment without mutating the parent process."""

    environment = dict(profile_environment)
    if env_file is not None:
        environment.update(load_runtime_environment_file(env_file))
    environment.update(process_environment if process_environment is not None else os.environ)
    return environment
