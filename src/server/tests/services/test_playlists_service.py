import json
from unittest.mock import MagicMock

from fastapi import HTTPException, status
import httpx
import pytest

from app.services.playlists_service import (
    fetch_listened_tracks,
    get_my_playlists_from_spotify,
    process_playlist_creation,
)
from app.db.models import Track

from ..conftest import db_session
from ..fixtures.constants import (
    CREATE_PLAYLIST_SERVICE_URL,
    GET_MY_PLAYLISTS_URL,
    SPOTIFY_HEADERS_EXAMPLE,
)
from ..fixtures.playlists_fixtures import (
    mock_async_client_get,
    mock_config_env,
    mock_get_spotify_headers,
    mock_get_current_user_id,
    mock_fetch_listened_tracks,
    mock_create_playlist_on_spotify,
    mock_async_client_post,
)


@pytest.mark.asyncio
async def test_get_my_playlists_from_spotify_success(
    db_session, mock_get_spotify_headers, mock_async_client_get, mock_get_current_user_id
):
    mock_request = httpx.Request("GET", "mock_request")
    mock_async_client_get.return_value = httpx.Response(
        status_code=status.HTTP_200_OK,
        json={"playlist1": "playlist1", "playlist2": "playlist2"},
        request=mock_request,
    )
    response = await get_my_playlists_from_spotify(0, 10, db_session)
    assert response == {"playlist1": "playlist1", "playlist2": "playlist2"}
    mock_async_client_get.assert_awaited_with(GET_MY_PLAYLISTS_URL, headers=SPOTIFY_HEADERS_EXAMPLE)


@pytest.mark.asyncio
async def test_get_my_playlists_from_spotify_failure(
    db_session, mock_get_spotify_headers, mock_async_client_get, mock_get_current_user_id
):
    mock_request = httpx.Request("GET", "mock_request")
    mock_async_client_get.return_value = httpx.Response(
        status_code=status.HTTP_404_NOT_FOUND, json={"ERROR": "ERROR"}, request=mock_request
    )
    with pytest.raises(HTTPException) as exc:
        await get_my_playlists_from_spotify(0, 10, db_session)
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == json.dumps({"ERROR": "ERROR"})
    mock_async_client_get.assert_awaited_with(GET_MY_PLAYLISTS_URL, headers=SPOTIFY_HEADERS_EXAMPLE)
    mock_get_spotify_headers.assert_called_once_with(db_session)


@pytest.mark.asyncio
async def test_process_playlist_creation_success(
    db_session,
    mock_get_spotify_headers,
    mock_async_client_post,
    mock_get_current_user_id,
    mock_fetch_listened_tracks,
    mock_create_playlist_on_spotify,
):
    mock_request = httpx.Request("POST", "mock_request")
    mock_async_client_post.return_value = httpx.Response(200, json={}, request=mock_request)
    response = await process_playlist_creation("test", db_session)
    assert response == {"message": "The 'test' playlist created successfully."}
    mock_async_client_post.assert_awaited_with(
        CREATE_PLAYLIST_SERVICE_URL,
        headers=SPOTIFY_HEADERS_EXAMPLE,
        json={"uris": ["spotify:track:10", "spotify:track:20"]},
    )


@pytest.mark.asyncio
async def test_process_playlist_creation_failure(
    db_session,
    mock_get_spotify_headers,
    mock_async_client_post,
    mock_get_current_user_id,
    mock_fetch_listened_tracks,
    mock_create_playlist_on_spotify,
):
    mock_request = httpx.Request("POST", "mock_request")
    mock_async_client_post.return_value = httpx.Response(
        status.HTTP_404_NOT_FOUND, json={"ERROR": "ERROR"}, request=mock_request
    )
    with pytest.raises(HTTPException) as exc:
        await process_playlist_creation("test", db_session)
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == json.dumps({"ERROR": "ERROR"})
    mock_async_client_post.assert_awaited_with(
        CREATE_PLAYLIST_SERVICE_URL,
        headers=SPOTIFY_HEADERS_EXAMPLE,
        json={"uris": ["spotify:track:10", "spotify:track:20"]},
    )


def test_fetch_listened_tracks_success(db_session):
    test_track = Track(title="Test Track", spotify_id="test_id", listened_count=5)
    db_session.add(test_track)
    db_session.commit()
    response = fetch_listened_tracks(db_session)
    assert len(response) == 1
    fetched_track = response[0]
    assert isinstance(fetched_track, Track)
    assert fetched_track.title == test_track.title
    assert fetched_track.spotify_id == test_track.spotify_id
    assert fetched_track.listened_count == test_track.listened_count


def test_fetch_listened_tracks_failure(db_session):
    test_track = Track(title="Test Track", spotify_id="test_id", listened_count=0)
    db_session.add(test_track)
    db_session.commit()
    with pytest.raises(HTTPException) as exc:
        fetch_listened_tracks(db_session)
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "No tracks you have listened to were found."
