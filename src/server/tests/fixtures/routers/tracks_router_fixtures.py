from unittest.mock import patch

import pytest


@pytest.fixture(scope="function")
def mock_get_current_track():
    with patch("app.routers.tracks_router.get_current_track") as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_is_user_authorized():
    with patch("app.routers.tracks_router.is_user_authorized") as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_poll_playback_state():
    with patch("app.routers.tracks_router.poll_playback_state") as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_get_recently_played_tracks():
    with patch("app.routers.tracks_router.get_recently_played_tracks") as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_get_playback_state():
    with patch("app.routers.tracks_router.get_playback_state") as mock:
        yield mock
