import httpx
import pytest
from app.services.spotify_auth_service import get_current_spotify_user_id, get_spotify_user
from fastapi import HTTPException, status
from httpx import HTTPStatusError

from ..conftest import db_session
from ..fixtures.constants import (
    GET_CURRENT_USER_URL,
    SPOTIFY_HEADERS_EXAMPLE,
    USER_DATA_EXAMPLE,
    USER_DATA_NO_ID_EXAMPLE,
    USER_ID_EXAMPLE,
)
from ..fixtures.services.spotify_auth_service_fixtures import (
    mock_async_client_get,
    mock_build_spotify_auth_headers,
    mock_build_spotify_token_request_data,
    mock_config_env,
    mock_exchange_token_with_spotify,
    mock_get_current_user,
    mock_get_spotify_headers,
    mock_get_spotify_user,
    mock_save_spotify_token,
)


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


@pytest.mark.asyncio
async def test_get_current_spotify_user_id_success(db_session, mock_get_spotify_user):
    mock_get_spotify_user.return_value = USER_DATA_EXAMPLE
    response = await get_current_spotify_user_id(USER_DATA_EXAMPLE["id"], db_session)
    assert response == USER_DATA_EXAMPLE["id"]
    mock_get_spotify_user.assert_awaited_once_with(USER_DATA_EXAMPLE["id"], db_session)


@pytest.mark.asyncio
async def test_get_current_spotify_user_id_failure(db_session, mock_get_spotify_user):
    mock_get_spotify_user.return_value = USER_DATA_NO_ID_EXAMPLE
    with pytest.raises(HTTPException) as exc:
        await get_current_spotify_user_id(USER_DATA_EXAMPLE["id"], db_session)
    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == "Failed to fetch current user ID"
