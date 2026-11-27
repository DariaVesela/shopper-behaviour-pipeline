import pytest

from tests.integration.stack import run_or_fail


@pytest.fixture(scope="session")
def stack_running() -> None:
    """Start the local services with `make up`. They are left running afterwards on purpose:
    local work may be using them, and `make up` is idempotent. CI stops them with `make clean`."""
    run_or_fail("make", "up")
