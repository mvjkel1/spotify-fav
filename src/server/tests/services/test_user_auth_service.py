from unittest.mock import patch

import httpx
import pytest
from app.services.user_auth_service import (
    generate_spotify_login_url,
    get_current_user,
    get_current_user_id,
    handle_spotify_callback,
)
from fastapi import HTTPException, status
from fastapi.responses import RedirectResponse

from ..conftest import db_session
from ..fixtures.constants import (
    ACCESS_TOKEN_EXAMPLE,
    USER_DATA_EXAMPLE,
    USER_DATA_EXAMPLE_MALFORMED,
)
from ..fixtures.services.user_auth_service_fixtures import (
    mock_async_client_get,
    mock_async_client_post,
    mock_config_env,
    mock_generate_random_string,
    mock_get_current_user_service,
    mock_get_spotify_headers,
)


@pytest.mark.asyncio
async def test_get_current_user_success(
    db_session, mock_get_spotify_headers, mock_async_client_get
):
    mock_async_client_get.return_value = httpx.Response(status_code=200, json=USER_DATA_EXAMPLE)
    result = await get_current_user(db_session)
    assert result == USER_DATA_EXAMPLE


@pytest.mark.asyncio
async def test_get_current_user_failure(db_session):
    with pytest.raises(HTTPException) as exc:
        await get_current_user(db_session)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert (
        exc.value.detail
        == "Access token does not exist in the database, login first to generate one."
    )


@pytest.mark.asyncio
async def test_get_current_user_id_success(mock_get_current_user_service, db_session):
    mock_get_current_user_service.return_value = USER_DATA_EXAMPLE
    result = await get_current_user_id(db_session)
    assert result == "user123"


@pytest.mark.asyncio
async def test_get_current_user_id_failure(mock_get_current_user_service, db_session):
    mock_get_current_user_service.return_value = USER_DATA_EXAMPLE_MALFORMED
    with pytest.raises(HTTPException) as exc:
        await get_current_user_id(db_session)
    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == "Failed to fetch current user ID"


async def test_generate_spotify_login_url(mock_config_env, mock_generate_random_string):
    result = generate_spotify_login_url()
    assert result == {
        "login_url": "SPOTIFY_AUTH_URL?response_type=code&client_id=CLIENT_ID&scope=SPOTIFY_API_SCOPES&redirect_uri=REDIRECT_URI&state=str1ng"
    }


@pytest.mark.asyncio
async def test_handle_spotify_callback_missing_code(db_session):
    with pytest.raises(HTTPException) as exc:
        await handle_spotify_callback("", db_session)
    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == "Authorization code missing"


@pytest.mark.asyncio
@patch("app.services.user_auth_service.save_token")
async def test_handle_spotify_callback_success(
    mock_save_token, mock_async_client_post, mock_config_env, db_session
):
    mock_request = httpx.Request("POST", "mock_request")
    mock_async_client_post.return_value = httpx.Response(
        200, json=ACCESS_TOKEN_EXAMPLE, request=mock_request
    )
    result = await handle_spotify_callback("valid_code", db_session)
    mock_save_token.assert_called_once_with(
        "fake_access_token", "fake_refresh_token", 3600, db_session
    )
    assert isinstance(result, RedirectResponse)
    assert result.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert result._headers.get("location") == "CALLBACK_REDIRECT_URL"


@pytest.mark.asyncio
async def test_handle_spotify_callback_invalid_token_response(
    mock_async_client_post, mock_config_env, db_session
):
    mock_request = httpx.Request("POST", "mock_request")
    mock_response_data = {"foo": "bar"}
    mock_async_client_post.return_value = httpx.Response(
        status_code=200, json=mock_response_data, request=mock_request
    )
    with pytest.raises(HTTPException) as exc:
        await handle_spotify_callback("valid_code", db_session)
    assert exc.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert exc.value.detail == "Failed to retrieve tokens from Spotify"


@pytest.mark.asyncio
async def test_handle_spotify_callback_spotify_http_error(mock_async_client_post, db_session):
    mock_async_client_post.side_effect = httpx.HTTPStatusError(
        message="Unauthorized",
        request=None,
        response=httpx.Response(status.HTTP_401_UNAUTHORIZED),
    )
    with pytest.raises(HTTPException) as exc:
        await handle_spotify_callback("valid_code", db_session)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "HTTP error occurred" in exc.value.detail


@pytest.mark.asyncio
async def test_handle_spotify_callback_spotify_request_error(mock_async_client_post, db_session):
    mock_async_client_post.side_effect = httpx.RequestError("Request failed", request=None)
    with pytest.raises(HTTPException) as exc:
        await handle_spotify_callback("valid_code", db_session)
    assert exc.value.status_code == status.HTTP_502_BAD_GATEWAY
    assert "Network error occurred: Request failed" in exc.value.detail
