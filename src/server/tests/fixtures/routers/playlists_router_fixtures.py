from unittest.mock import patch

import pytest


@pytest.fixture(scope="function")
def mock_get_playlists_from_spotify():
    with patch("app.routers.playlists_router.get_playlists_from_spotify") as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_process_playlist_creation():
    with patch("app.routers.playlists_router.process_playlist_creation") as mock:
        yield mock
