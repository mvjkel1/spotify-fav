from unittest.mock import patch
from fastapi import HTTPException, status
import httpx
import pytest

from app.services.tracks_service import (
    get_current_track,
    get_playback_state,
    get_recently_played_tracks,
    handle_playing_track,
)
from ..conftest import db_session
from ..fixtures.tracks_fixtures import (
    mock_get_spotify_headers,
    mock_async_client_get,
    mock_config_env,
    mock_extract_track_data,
    mock_process_playing_track,
    SPOTIFY_HEADERS_EXAMPLE,
)

GET_CURRENT_TRACK_URL = "https://api.spotify.com/v1/me/player/currently-playing"
GET_RECENTLY_PLAYED_TRACKS_URL = "https://api.spotify.com/v1/me/player/recently-played?limit=1"
GET_PLAYBACK_STATE_URL = "https://api.spotify.com/v1/me/player"


@pytest.mark.asyncio
async def test_get_current_track_success(
    db_session, mock_get_spotify_headers, mock_async_client_get, mock_config_env
):
    mock_async_client_get.return_value = httpx.Response(status_code=200, json={"track": "track123"})
    response = await get_current_track(db_session)
    mock_async_client_get.assert_awaited_with(
        GET_CURRENT_TRACK_URL,
        headers=SPOTIFY_HEADERS_EXAMPLE,
    )
    assert response == {"track": "track123"}


@pytest.mark.asyncio
async def test_get_current_track_failure(
    db_session, mock_get_spotify_headers, mock_async_client_get, mock_config_env
):
    mock_async_client_get.return_value = httpx.Response(status_code=status.HTTP_401_UNAUTHORIZED)
    with pytest.raises(HTTPException) as exc:
        await get_current_track(db_session)
    mock_async_client_get.assert_awaited_with(
        GET_CURRENT_TRACK_URL,
        headers=SPOTIFY_HEADERS_EXAMPLE,
    )
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Failed to fetch current track" in exc.value.detail


@pytest.mark.asyncio
async def test_get_recently_played_tracks_success(
    db_session, mock_get_spotify_headers, mock_async_client_get, mock_config_env
):
    mock_async_client_get.return_value = httpx.Response(
        status_code=200, json={"track1": "track1", "track2": "track2"}
    )
    response = await get_recently_played_tracks(db_session)
    mock_async_client_get.assert_awaited_with(
        GET_RECENTLY_PLAYED_TRACKS_URL,
        headers=SPOTIFY_HEADERS_EXAMPLE,
    )
    assert response == {"track1": "track1", "track2": "track2"}


@pytest.mark.asyncio
async def test_get_recently_played_tracks_failure(
    db_session, mock_get_spotify_headers, mock_async_client_get, mock_config_env
):
    mock_async_client_get.return_value = httpx.Response(status_code=status.HTTP_401_UNAUTHORIZED)
    with pytest.raises(HTTPException) as exc:
        await get_recently_played_tracks(db_session)
    mock_async_client_get.assert_awaited_with(
        GET_RECENTLY_PLAYED_TRACKS_URL,
        headers=SPOTIFY_HEADERS_EXAMPLE,
    )
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Failed to fetch recently played tracks" in exc.value.detail


@pytest.mark.asyncio
async def test_get_playback_state_success(
    db_session, mock_get_spotify_headers, mock_async_client_get, mock_config_env
):
    mock_async_client_get.return_value = httpx.Response(
        status_code=status.HTTP_200_OK, json={"state": "playing"}
    )
    response = await get_playback_state(db_session)
    mock_async_client_get.assert_awaited_with(
        GET_PLAYBACK_STATE_URL,
        headers=SPOTIFY_HEADERS_EXAMPLE,
    )
    assert response == {"state": "playing"}


@pytest.mark.asyncio
async def test_get_playback_state_failure(
    db_session, mock_get_spotify_headers, mock_async_client_get, mock_config_env
):
    mock_async_client_get.return_value = httpx.Response(status_code=status.HTTP_401_UNAUTHORIZED)
    with pytest.raises(HTTPException) as exc:
        await get_playback_state(db_session)
    mock_async_client_get.assert_awaited_with(
        GET_PLAYBACK_STATE_URL,
        headers=SPOTIFY_HEADERS_EXAMPLE,
    )
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Failed to fetch playback state" in exc.value.detail


@pytest.mark.asyncio
async def test_handle_playing_track_success(
    db_session,
    mock_process_playing_track,
):
    state = {
        "is_playing": True,
        "progress_ms": 10000,
        "item": {"duration_ms": 11112222, "name": "test track", "id": "test_track_id"},
    }
    await handle_playing_track(state, db_session)
    mock_process_playing_track.assert_awaited_with(
        None, True, False, "test track", "test_track_id", db_session
    )


@pytest.mark.asyncio
async def test_handle_playing_track_failure(
    db_session,
    mock_process_playing_track,
):
    state = {
        "is_playing": False,
        "progress_ms": 10000,
        "item": {"duration_ms": 11112222, "name": "test track", "id": "test_track_id"},
    }
    await handle_playing_track(state, db_session)
    mock_process_playing_track.assert_not_awaited()
