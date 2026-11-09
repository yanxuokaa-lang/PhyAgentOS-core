import inspect
from types import ModuleType

import pytest
from syrupy.assertion import SnapshotAssertion

import typesafe_sdk
from typesafe_sdk import AsyncTypeSafeClient, TypeSafeClient


@pytest.mark.parametrize("module", [typesafe_sdk, typesafe_sdk.constants], ids=lambda module: module.__name__)
def test_public_members(module: ModuleType, snapshot: SnapshotAssertion) -> None:
    members = module.__all__ if module is typesafe_sdk else (name for name in vars(module) if not name.startswith("_"))
    assert sorted(members) == snapshot


def test_package_exports() -> None:
    assert not any(name.startswith("_") for name in typesafe_sdk.__all__)


@pytest.mark.parametrize("client_type", [AsyncTypeSafeClient, TypeSafeClient])
def test_constructor_kwargs(client_type: type[AsyncTypeSafeClient] | type[TypeSafeClient], snapshot: SnapshotAssertion) -> None:
    parameters = inspect.signature(client_type).parameters
    assert list(parameters) == snapshot
    assert all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in parameters.values())
    assert all(parameter.default is None for parameter in parameters.values())
