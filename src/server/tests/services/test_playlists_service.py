from unittest.mock import patch

from fastapi import HTTPException
import httpx
import pytest

from app.services.playlists_service import get_my_playlists_from_spotify

from ..conftest import db_session
from ..fixtures.constants import GET_MY_PLAYLISTS_URL, SPOTIFY_HEADERS_EXAMPLE
from ..fixtures.playlists_fixtures import (
    mock_async_client_get,
    mock_config_env,
    mock_get_spotify_headers,
)


@pytest.mark.asyncio
async def test_get_my_playlists_from_spotify_success(
    db_session, mock_get_spotify_headers, mock_async_client_get
):
    mock_request = httpx.Request("GET", "mock_request")
    mock_async_client_get.return_value = httpx.Response(
        status_code=200,
        json={"playlist1": "playlist1", "playlist2": "playlist2"},
        request=mock_request,
    )
    response = await get_my_playlists_from_spotify("1", 0, 10, db_session)
    assert response == {"playlist1": "playlist1", "playlist2": "playlist2"}
    mock_async_client_get.assert_awaited_with(GET_MY_PLAYLISTS_URL, headers=SPOTIFY_HEADERS_EXAMPLE)


@pytest.mark.asyncio
async def test_get_my_playlists_from_spotify_failure(
    db_session, mock_get_spotify_headers, mock_async_client_get
):
    mock_request = httpx.Request("GET", "mock_request")
    mock_async_client_get.return_value = httpx.Response(
        status_code=404, json={"ERROR": "ERROR"}, request=mock_request
    )
    with pytest.raises(HTTPException) as exc:
        await get_my_playlists_from_spotify("1", 0, 10, db_session)
    assert exc.value.status_code == 404
    assert exc.value.detail == '{"ERROR": "ERROR"}'
    mock_async_client_get.assert_awaited_with(GET_MY_PLAYLISTS_URL, headers=SPOTIFY_HEADERS_EXAMPLE)
    mock_get_spotify_headers.assert_called_once_with(db_session)
