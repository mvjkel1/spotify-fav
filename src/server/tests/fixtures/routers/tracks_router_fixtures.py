from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(scope="function")
def mock_get_current_track():
    with patch("app.routers.tracks_router.get_current_track", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_is_user_authorized():
    with patch("app.routers.tracks_router.is_user_authorized", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_poll_playback_state():
    with patch("app.routers.tracks_router.poll_playback_state", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_get_recently_played_tracks():
    with patch(
        "app.routers.tracks_router.get_recently_played_tracks", new_callable=AsyncMock
    ) as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_get_playback_state():
    with patch("app.routers.tracks_router.get_playback_state", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_set_user_polling_status():
    with patch("app.routers.tracks_router.set_user_polling_status", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_start_polling_tracks():
    with patch("app.routers.tracks_router.start_polling_tracks", new_callable=AsyncMock) as mock:
        yield mock
