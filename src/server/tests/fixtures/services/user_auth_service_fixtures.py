from unittest.mock import AsyncMock, patch

import pytest

from ..constants import ENV_CONFIG_EXAMPLE, SPOTIFY_HEADERS_EXAMPLE


@pytest.fixture(scope="function")
def mock_get_spotify_headers():
    with patch(
        "app.services.user_auth_service.get_spotify_headers",
        return_value=SPOTIFY_HEADERS_EXAMPLE,
    ) as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_async_client_get():
    with patch(
        "app.services.user_auth_service.httpx.AsyncClient.get", new_callable=AsyncMock
    ) as mock:
        yield mock


@pytest.fixture(scope="module")
def mock_async_client_post():
    with patch(
        "app.services.user_auth_service.httpx.AsyncClient.post", new_callable=AsyncMock
    ) as mock:
        yield mock


@pytest.fixture(scope="module", autouse=True)
def mock_config_env():
    with patch(
        "app.services.user_auth_service.config",
        ENV_CONFIG_EXAMPLE,
    ) as mock:
        yield mock


@pytest.fixture(scope="module")
def mock_generate_random_string():
    with patch(
        "app.services.user_auth_service.generate_random_string", return_value="str1ng"
    ) as mock:
        yield mock


@pytest.fixture(scope="module")
def mock_get_current_user_service():
    with patch("app.services.user_auth_service.get_current_user") as mock:
        yield mock
