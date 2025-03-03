from unittest.mock import AsyncMock, patch

import pytest

from app.db.models import Track, User

from ..constants import ENV_CONFIG_EXAMPLE, SPOTIFY_HEADERS_EXAMPLE, SPOTIFY_USER_ID_EXAMPLE


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
def mock_get_current_user_db():
    with patch(
        "app.services.playlists_service.get_current_user_db",
        return_value=User(id=1, spotify_uid=1, email="user@example.com", hashed_password="P!w!D"),
    ) as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_get_current_spotify_user_id():
    with patch(
        "app.services.playlists_service.get_current_spotify_user_id",
        return_value=SPOTIFY_USER_ID_EXAMPLE,
    ) as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_create_playlist():
    with patch("app.services.playlists_service.create_playlist") as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_filter_new_tracks():
    with patch("app.services.playlists_service.filter_new_tracks") as mock:
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


@pytest.fixture(scope="function")
def mock_get_all_playlists():
    with patch("app.services.playlists_service.get_all_playlists") as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_sync_playlists():
    with patch("app.services.playlists_service.sync_playlists") as mock:
        yield mock


class MockRedisClient:
    def __init__(self, url=None, token=None):
        self.url = url or ENV_CONFIG_EXAMPLE["REDIS_URL"]
        self.token = token or ENV_CONFIG_EXAMPLE["REDIS_TOKEN"]
        self.cache = {}

    async def get(self, key: str):
        return self.cache.get(key)

    async def set(self, key: str, value: str, ex: int = None):
        self.cache[key] = value

    async def close(self):
        self.cache.clear()


@pytest.fixture(scope="function")
def mock_redis():
    with patch("app.services.playlists_service.Redis", MockRedisClient) as mock:
        yield mock
