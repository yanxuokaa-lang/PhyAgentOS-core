"""Check an installed adapter distribution."""

# ruff: noqa: INP001 - Standalone CI script.

import asyncio
import sys
from importlib.metadata import version

import system_one_adapter
from system_one_adapter import AsyncSystemOneAdapterClient, SystemOneAdapterClient


async def main() -> None:
    """Check the installed version and initialize both clients."""
    if version("system-one-adapter") != sys.argv[1]:
        raise RuntimeError("Installed distribution version does not match the release")
    if system_one_adapter.__version__ != sys.argv[1]:
        raise RuntimeError("Exported version does not match the release")
    with SystemOneAdapterClient(structured_outputs=False, llm_answer_mode="discrete"):
        pass
    async with AsyncSystemOneAdapterClient(structured_outputs=False, llm_answer_mode="discrete"):
        pass


if __name__ == "__main__":
    asyncio.run(main())
