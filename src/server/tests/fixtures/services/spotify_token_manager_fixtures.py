from time import time
from unittest.mock import patch

import pytest

from app.db.models import SpotifyAccessToken

from ..constants import ENV_CONFIG_EXAMPLE


@pytest.fixture(scope="function")
def mock_spotify_valid_token():
    return SpotifyAccessToken(
        access_token="valid_token",
        refresh_token="refresh_token",
        user_id=1,
        expires_at=time() + 3600,
    )


@pytest.fixture(scope="function")
def mock_spotify_expired_token():
    return SpotifyAccessToken(
        access_token="expired_token",
        refresh_token="refresh_token",
        user_id=1,
        expires_at=time() - 100,
    )


@pytest.fixture(scope="function")
def mock_refresh_access_token():
    with patch("app.services.spotify_token_manager.refresh_spotify_access_token") as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_async_client_post():
    with patch("app.services.spotify_token_manager.httpx.AsyncClient.post") as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_get_spotify_token():
    with patch("app.services.spotify_token_manager.get_spotify_token") as mock:
        yield mock


@pytest.fixture(scope="module", autouse=True)
def mock_config_env():
    with patch(
        "app.services.spotify_token_manager.config",
        ENV_CONFIG_EXAMPLE,
    ) as mock:
        yield mock
