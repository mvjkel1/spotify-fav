from unittest.mock import patch, AsyncMock

import pytest

from tests.fixtures.constants import ENV_CONFIG_EXAMPLE, SPOTIFY_HEADERS_EXAMPLE


@pytest.fixture(scope="function")
def mock_get_spotify_headers():
    with patch(
        "app.services.spotify_auth_service.get_spotify_headers",
        return_value=SPOTIFY_HEADERS_EXAMPLE,
    ) as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_async_client_get():
    with patch(
        "app.services.spotify_auth_service.httpx.AsyncClient.get", new_callable=AsyncMock
    ) as mock:
        yield mock


@pytest.fixture(scope="module", autouse=True)
def mock_config_env():
    with patch(
        "app.services.spotify_auth_service.config",
        ENV_CONFIG_EXAMPLE,
    ) as mock:
        yield mock
