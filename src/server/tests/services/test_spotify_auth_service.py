import httpx
import pytest
from fastapi import status
from httpx import HTTPStatusError

from app.services.spotify_auth_service import get_spotify_user
from ..fixtures.constants import GET_CURRENT_USER_URL, SPOTIFY_HEADERS_EXAMPLE, USER_ID_EXAMPLE
from ..fixtures.services.spotify_auth_service_fixtures import (
    mock_async_client_get,
    mock_config_env,
    mock_get_spotify_headers,
)

from ..conftest import db_session


@pytest.mark.asyncio
async def test_get_spotify_user_success(
    db_session, mock_get_spotify_headers, mock_async_client_get
):
    mock_request = httpx.Request("GET", "mock_request")
    mock_async_client_get.return_value = httpx.Response(
        status_code=status.HTTP_200_OK,
        json={"id": USER_ID_EXAMPLE, "username": "name"},
        request=mock_request,
    )
    response = await get_spotify_user(USER_ID_EXAMPLE, db_session)
    assert response == {"id": USER_ID_EXAMPLE, "username": "name"}
    mock_async_client_get.assert_awaited_once_with(
        GET_CURRENT_USER_URL, headers=SPOTIFY_HEADERS_EXAMPLE
    )


@pytest.mark.asyncio
async def test_get_spotify_user_failure(
    db_session, mock_get_spotify_headers, mock_async_client_get
):
    mock_request = httpx.Request("GET", "mock_request")
    mock_async_client_get.return_value = httpx.Response(
        status_code=status.HTTP_400_BAD_REQUEST,
        json={"ERROR": "ERROR"},
        request=mock_request,
    )
    with pytest.raises(HTTPStatusError) as exc:
        await get_spotify_user(USER_ID_EXAMPLE, db_session)
    assert exc.value.response.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.response._content == b'{"ERROR": "ERROR"}'
