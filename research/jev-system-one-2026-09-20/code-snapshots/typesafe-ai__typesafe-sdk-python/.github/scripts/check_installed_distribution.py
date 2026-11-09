"""Check an installed SDK distribution."""

# ruff: noqa: INP001 - Standalone CI script.

import asyncio
import sys
from importlib.metadata import version

import typesafe_sdk
from typesafe_sdk import AsyncTypeSafeClient, TypeSafeClient


async def main() -> None:
    """Check the installed version and initialize both clients."""
    if version("typesafe-sdk") != sys.argv[1]:
        raise RuntimeError("Installed distribution version does not match the release")
    if typesafe_sdk.__version__ != sys.argv[1]:
        raise RuntimeError("Exported SDK version does not match the release")
    with TypeSafeClient(api_key="release-smoke-test"):
        pass
    async with AsyncTypeSafeClient(api_key="release-smoke-test"):
        pass


if __name__ == "__main__":
    asyncio.run(main())
