from unittest.mock import AsyncMock, patch

import pytest

from .constants import SPOTIFY_HEADERS_EXAMPLE, TRACK_DATA_EXAMPLE, ENV_CONFIG_EXAMPLE


@pytest.fixture(scope="function")
def mock_get_spotify_headers():
    with patch(
        "app.services.tracks_service.get_spotify_headers",
        return_value=SPOTIFY_HEADERS_EXAMPLE,
    ) as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_async_client_get():
    with patch("app.services.tracks_service.httpx.AsyncClient.get", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture(scope="module", autouse=True)
def mock_config_env():
    with patch(
        "app.services.tracks_service.config",
        ENV_CONFIG_EXAMPLE,
    ) as mock:
        yield mock


@pytest.fixture(scope="module")
def mock_extract_track_data():
    with patch(
        "app.services.tracks_service.extract_track_data",
        return_value=TRACK_DATA_EXAMPLE,
    ) as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_process_playing_track():
    with patch("app.services.tracks_service.process_playing_track", new_callable=AsyncMock) as mock:
        yield mock


# @pytest.fixture(scope="module")
# def mock_check_track_progress():
#     with patch(
#         "app.services.tracks_service.check_track_progress", return_value=(True, False)
#     ) as mock:
#         yield mock
