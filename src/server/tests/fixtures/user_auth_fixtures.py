from unittest.mock import AsyncMock, patch
import pytest
from ..utils.utils import SPOTIFY_HEADERS_EXAMPLE


@pytest.fixture(scope="function")
def mock_get_spotify_headers():
    with patch(
        "app.services.user_auth_service.get_spotify_headers",
        return_value=SPOTIFY_HEADERS_EXAMPLE,
    ) as mock:
        yield mock


@pytest.fixture(scope="module")
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


@pytest.fixture(scope="module")
def mock_get_current_user():
    with patch("app.services.user_auth_service.get_current_user") as mock:
        yield mock


@pytest.fixture(scope="module")
def mock_config_env():
    with patch(
        "app.services.user_auth_service.config",
        {
            "CLIENT_ID": "CLIENT_ID",
            "CLIENT_SECRET": "CLIENT_SECRET",
            "SPOTIFY_API_SCOPES": "SPOTIFY_API_SCOPES",
            "SPOTIFY_TOKEN_URL": "SPOTIFY_TOKEN_URL",
            "REDIRECT_URI": "REDIRECT_URI",
            "CALLBACK_REDIRECT_URL": "CALLBACK_REDIRECT_URL",
            "SPOTIFY_AUTH_URL": "SPOTIFY_AUTH_URL",
        },
    ) as mock:
        yield mock


@pytest.fixture(scope="module")
def mock_generate_random_string():
    with patch(
        "app.services.user_auth_service.generate_random_string", return_value="str1ng"
    ) as mock:
        yield mock
