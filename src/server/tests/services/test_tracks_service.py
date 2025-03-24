from unittest.mock import patch
from fastapi import HTTPException, status
import httpx
import pytest

from app.services.tracks_service import get_current_track, get_recently_played_tracks
from ..conftest import db_session
from ..fixtures.tracks_fixtures import (
    mock_get_spotify_headers,
    mock_async_client_get,
    mock_config_env,
)


@pytest.mark.asyncio
async def test_get_current_track_success(
    db_session, mock_get_spotify_headers, mock_async_client_get, mock_config_env
):
    mock_async_client_get.return_value = httpx.Response(status_code=200, json={"track": "track123"})
    response = await get_current_track(db_session)
    assert response == {"track": "track123"}


@pytest.mark.asyncio
async def test_get_current_track_failure(
    db_session, mock_get_spotify_headers, mock_async_client_get, mock_config_env
):
    mock_async_client_get.return_value = httpx.Response(
        status_code=status.HTTP_401_UNAUTHORIZED, json={"ERROR": "ERROR"}
    )
    with pytest.raises(HTTPException) as exc:
        await get_current_track(db_session)
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
    assert response == {"track1": "track1", "track2": "track2"}


@pytest.mark.asyncio
async def test_get_recently_played_tracks_failure(
    db_session, mock_get_spotify_headers, mock_async_client_get, mock_config_env
):
    mock_async_client_get.return_value = httpx.Response(
        status_code=status.HTTP_401_UNAUTHORIZED, json={"ERROR": "ERROR"}
    )
    with pytest.raises(HTTPException) as exc:
        await get_recently_played_tracks(db_session)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Failed to fetch recently played tracks" in exc.value.detail
