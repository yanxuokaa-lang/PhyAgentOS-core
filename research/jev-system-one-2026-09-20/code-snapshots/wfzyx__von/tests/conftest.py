import pytest
import von


@pytest.fixture(autouse=True)
def reset_to_default_backend():
    yield
    von.set_backend("von-1.0")
