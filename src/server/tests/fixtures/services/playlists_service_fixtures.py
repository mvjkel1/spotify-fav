from unittest.mock import AsyncMock, patch

import pytest

from app.db.models import Track

from ..constants import ENV_CONFIG_EXAMPLE, SPOTIFY_HEADERS_EXAMPLE


@pytest.fixture(scope="function")
def mock_get_spotify_headers():
    with patch(
        "app.services.playlists_service.get_spotify_headers",
        return_value=SPOTIFY_HEADERS_EXAMPLE,
    ) as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_async_client_get():
    with patch(
        "app.services.playlists_service.httpx.AsyncClient.get", new_callable=AsyncMock
    ) as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_async_client_post():
    with patch(
        "app.services.playlists_service.httpx.AsyncClient.post", new_callable=AsyncMock
    ) as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_get_current_user_id():
    with patch("app.services.playlists_service.get_current_user_id", return_value=1) as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_fetch_listened_tracks():
    with patch(
        "app.services.playlists_service.fetch_listened_tracks",
        return_value=[
            Track(
                id="1",
                spotify_id="10",
                title="song1",
            ),
            Track(
                id="2",
                spotify_id="20",
                title="song2",
            ),
        ],
    ) as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_create_playlist_on_spotify():
    with patch(
        "app.services.playlists_service.create_playlist_on_spotify", return_value=10
    ) as mock:
        yield mock


@pytest.fixture(scope="module", autouse=True)
def mock_config_env():
    with patch(
        "app.services.playlists_service.config",
        ENV_CONFIG_EXAMPLE,
    ) as mock:
        yield mock