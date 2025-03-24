from unittest.mock import patch

import httpx
import pytest
import status
from fastapi import HTTPException, Request

from app.endpoints.user_auth import (callback, get_current_user,
                                     get_current_user_id, login)

from .conftest import db_session, test_client

HEADERS = {
    "Authorization": "Bearer access_token",
    "Content-Type": "application/json",
}

USER_DATA = {
    "id": "user123",
    "display_name": "Test User",
    "email": "testuser@example.com",
}

MOCK_DOTENV_VALUES = {
    "CLIENT_ID": "mock_client_id",
    "SPOTIFY_API_SCOPES": "mock_scope",
    "REDIRECT_URI": "http://mock_redirect.com",
    "SPOTIFY_AUTH_URL": "http://mock_auth_url.com",
}


@pytest.fixture
def mock_config():
    with patch("app.endpoints.user_auth.config", MOCK_DOTENV_VALUES) as mock:
        yield mock


@pytest.mark.asyncio
@patch(
    "app.endpoints.user_auth.httpx.AsyncClient.get",
    return_value=httpx.Response(
        200,
        json=USER_DATA,
    ),
)
@patch("app.endpoints.user_auth.get_spotify_headers", return_value=HEADERS)
@pytest.mark.parametrize("expected_output", [USER_DATA])
async def test_get_current_user_success(
    mock_spotify_headers, mock_async_client, expected_output
):
    result = await get_current_user()
    assert result == expected_output
    mock_async_client.assert_called_once_with(
        "https://api.spotify.com/v1/me",
        headers=HEADERS,
    )


@pytest.mark.asyncio
@patch("app.endpoints.user_auth.get_spotify_headers", return_value=HEADERS)
@patch(
    "app.endpoints.user_auth.httpx.AsyncClient.get",
    side_effect=HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
    ),
)
@pytest.mark.parametrize(
    "expected_status_code, expected_message",
    [(status.HTTP_401_UNAUTHORIZED, "Unauthorized")],
)
async def test_get_current_user_failure(
    mock_async_client,
    mock_spotify_headers,
    expected_status_code,
    expected_message,
):
    with pytest.raises(HTTPException) as exc:
        await get_current_user()

    assert exc.value.status_code == expected_status_code
    assert expected_message in exc.value.detail


@pytest.mark.asyncio
@patch("app.endpoints.user_auth.get_current_user", return_value=USER_DATA)
async def test_get_current_user_id_success(mock_get_current_user, db_session):
    user_id = await get_current_user_id(db_session)
    assert user_id == "user123"


@pytest.mark.asyncio
@patch(
    "app.endpoints.user_auth.get_current_user",
    side_effect=HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
    ),
)
@pytest.mark.parametrize(
    "expected_status_code, expected_message",
    [(status.HTTP_401_UNAUTHORIZED, "Unauthorized")],
)
async def test_get_current_user_id_failure(
    mock_get_current_user,
    db_session,
    expected_status_code,
    expected_message,
):
    with pytest.raises(HTTPException) as exc:
        await get_current_user_id(db_session)
    assert exc.value.status_code == expected_status_code
    assert expected_message in exc.value.detail


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_output",
    [
        {
            "login_url": "http://mock_auth_url.com?response_type=code&client_id=mock_client_id&scope=mock_scope&redirect_uri=http%3A%2F%2Fmock_redirect.com&state=randomstring123"
        }
    ],
)
@patch("app.endpoints.user_auth.generate_random_string", return_value="randomstring123")
async def test_login(
    mock_generate_random_string,
    mock_config,
    expected_output,
):
    response = await login()
    assert response == expected_output


@pytest.mark.asyncio
async def test_callback_missing_code():
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "headers": {},
            "query_string": "",
            "url": "url",
        }
    )
    with pytest.raises(HTTPException) as exc:
        await callback(request)
    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == "Authorization code not found in request"


@pytest.mark.asyncio
@patch("app.endpoints.user_auth.save_token")
@patch(
    "app.endpoints.user_auth.httpx.AsyncClient.post",
    return_value=httpx.Response(
        200, json={"access_token": "123", "refresh_token": "321", "expires_in": 0}
    ),
)
async def test_callback_success(mock_mock_async_client, mock_save_token, db_session):
    query_string = "code=code123"
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "headers": {},
            "query_string": query_string,
            "url": "url",
        }
    )
    response = await callback(request, db_session)
    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    mock_save_token.assert_called_once_with("123", "321", 0, db_session)


@pytest.mark.asyncio
async def test_callback_failure(db_session):
    query_string = "code=code123"
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "headers": {},
            "query_string": query_string,
            "url": "url",
        }
    )
    with pytest.raises(HTTPException) as exc:
        await callback(request)
    assert exc.value.detail == "Failed to retrieve tokens from Spotify API"
    assert exc.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
