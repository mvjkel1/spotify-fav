from unittest.mock import AsyncMock, patch

import pytest

from tests.fixtures.constants import ENV_CONFIG_EXAMPLE


@pytest.fixture(scope="function")
def mock_get_current_user_router():
    with patch("app.routers.user_auth_router.get_current_user", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture(scope="module", autouse=True)
def mock_config_env():
    with patch(
        "app.routers.user_auth_router.config",
        ENV_CONFIG_EXAMPLE,
    ) as mock:
        yield mock
