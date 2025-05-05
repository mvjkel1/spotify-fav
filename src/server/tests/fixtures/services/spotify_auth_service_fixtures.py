from unittest.mock import AsyncMock, patch

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


@pytest.fixture(scope="function")
def mock_get_spotify_user():
    with patch("app.services.spotify_auth_service.get_spotify_user") as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_build_spotify_auth_headers():
    with patch("app.services.spotify_auth_service.build_spotify_auth_headers") as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_build_spotify_token_request_data():
    with patch("app.services.spotify_auth_service.build_spotify_token_request_data") as mock:
        yield mock @ pytest.fixture(scope="function")


@pytest.fixture(scope="function")
def mock_exchange_token_with_spotify():
    with patch("app.services.spotify_auth_service.exchange_token_with_spotify") as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_get_current_user():
    with patch("app.services.spotify_auth_service.get_current_user") as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_save_spotify_token():
    with patch("app.services.spotify_auth_service.save_spotify_token") as mock:
        yield mock


@pytest.fixture(scope="module", autouse=True)
def mock_config_env():
    with patch(
        "app.services.spotify_auth_service.config",
        ENV_CONFIG_EXAMPLE,
    ) as mock:
        yield mock
