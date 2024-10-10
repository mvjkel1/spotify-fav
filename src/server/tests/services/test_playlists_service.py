import json

from fastapi import HTTPException, status
import httpx
import pytest

from app.services.playlists_service import get_my_playlists_from_spotify, create_playlist_service

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
async def test_create_playlist_service_success(
    db_session,
    mock_get_spotify_headers,
    mock_async_client_post,
    mock_get_current_user_id,
    mock_fetch_listened_tracks,
    mock_create_playlist_on_spotify,
):
    mock_request = httpx.Request("POST", "mock_request")
    mock_async_client_post.return_value = httpx.Response(200, json={}, request=mock_request)
    response = await create_playlist_service("test", db_session)
    assert response == {"message": "The 'test' playlist created successfully."}
    mock_async_client_post.assert_awaited_with(
        CREATE_PLAYLIST_SERVICE_URL,
        headers=SPOTIFY_HEADERS_EXAMPLE,
        json={"uris": ["spotify:track:10", "spotify:track:20"]},
    )


@pytest.mark.asyncio
async def test_create_playlist_service_failure(
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
        await create_playlist_service("test", db_session)
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == json.dumps({"ERROR": "ERROR"})
    mock_async_client_post.assert_awaited_with(
        CREATE_PLAYLIST_SERVICE_URL,
        headers=SPOTIFY_HEADERS_EXAMPLE,
        json={"uris": ["spotify:track:10", "spotify:track:20"]},
    )
