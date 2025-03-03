import pytest
from unittest.mock import AsyncMock, patch


TRACK_DATA_EXAMPLE = (10000, 12000, "Test track", "test_track_id")

SPOTIFY_HEADERS_EXAMPLE = {
    "Authorization": "Bearer access_token",
    "Content-Type": "application/json",
}


@pytest.fixture(scope="function")
def mock_get_spotify_headers():
    with patch(
        "app.services.tracks_service.get_spotify_headers",
        return_value=SPOTIFY_HEADERS_EXAMPLE,
    ) as mock:
        yield mock


@pytest.fixture(scope="module")
def mock_async_client_get():
    with patch("app.services.tracks_service.httpx.AsyncClient.get", new_callable=AsyncMock) as mock:
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
