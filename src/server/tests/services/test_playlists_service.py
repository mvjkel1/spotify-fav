import json
from unittest.mock import MagicMock

import httpx
import pytest
from app.db.models import Track
from app.services.playlists_service import (
    cache_playlist_tracks,
    fetch_listened_tracks,
    get_playlists_from_spotify,
    process_playlist_creation,
)
from fastapi import HTTPException, status

from ..conftest import db_session
from ..fixtures.constants import (
    CREATE_PLAYLIST_SERVICE_URL,
    GET_MY_PLAYLISTS_URL,
    SPOTIFY_HEADERS_EXAMPLE,
)
from ..fixtures.services.playlists_service_fixtures import (
    mock_async_client_get,
    mock_async_client_post,
    mock_config_env,
    mock_create_playlist_on_spotify,
    mock_fetch_listened_tracks,
    mock_get_all_playlists,
    mock_get_current_user_id,
    mock_get_spotify_headers,
)


@pytest.mark.asyncio
async def test_get_playlists_from_spotify_success(
    db_session,
    mock_get_spotify_headers,
    mock_async_client_get,
    mock_get_current_user_id,
):
    mock_request = httpx.Request("GET", "mock_request")
    mock_async_client_get.return_value = httpx.Response(
        status_code=status.HTTP_200_OK,
        json={"playlist1": "playlist1", "playlist2": "playlist2"},
        request=mock_request,
    )
    response = await get_playlists_from_spotify(0, 10, db_session)
    assert response == {"playlist1": "playlist1", "playlist2": "playlist2"}
    mock_async_client_get.assert_awaited_with(GET_MY_PLAYLISTS_URL, headers=SPOTIFY_HEADERS_EXAMPLE)


@pytest.mark.asyncio
async def test_get_playlists_from_spotify_failure(
    db_session,
    mock_get_spotify_headers,
    mock_async_client_get,
    mock_get_current_user_id,
):
    mock_request = httpx.Request("GET", "mock_request")
    mock_async_client_get.return_value = httpx.Response(
        status_code=status.HTTP_404_NOT_FOUND,
        json={"ERROR": "ERROR"},
        request=mock_request,
    )
    with pytest.raises(HTTPException) as exc:
        await get_playlists_from_spotify(0, 10, db_session)
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
    mock_get_all_playlists,
    mock_fetch_listened_tracks,
    mock_create_playlist_on_spotify,
):
    mock_request = httpx.Request("POST", "mock_request")
    mock_async_client_post.return_value = httpx.Response(200, json={}, request=mock_request)
    response = await process_playlist_creation("test", db_session)
    assert response == {"message": "The 'test' playlist was created successfully."}
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
    mock_get_all_playlists,
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


@pytest.mark.asyncio
async def test_cache_playlist_tracks(db_session, mock_get_spotify_headers, mock_async_client_get):
    playlists = [
        {"uri": "spotify:playlist:1"},
        {"uri": "spotify:playlist:2"},
    ]
    mocked_responses = [
        {
            "tracks": {
                "items": [
                    {"track": {"name": "Track A"}},
                    {"track": {"name": "Track B"}},
                ]
            }
        },
        {
            "tracks": {
                "items": [
                    {"track": {"name": "Track C"}},
                    {"track": {"name": "Track D"}},
                ]
            }
        },
    ]

    mock_request = httpx.Request("GET", "mock_request")
    mock_async_client_get.side_effect = [
        httpx.Response(200, json=mocked_response, request=mock_request)
        for mocked_response in mocked_responses
    ]
    result = await cache_playlist_tracks(playlists, db_session)
    assert result == {"1": {"Track A", "Track B"}, "2": {"Track D", "Track C"}}
    assert mock_async_client_get.call_count == len(playlists)
