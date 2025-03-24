import httpx
import pytest
from fastapi import HTTPException, status

from ..conftest import db_session
from ..fixtures.constants import SPOTIFY_HEADERS_EXAMPLE, USER_DATA_EXAMPLE
from ..fixtures.user_auth_fixtures import (
    mock_async_client_get,
    mock_generate_spotify_login_url,
    mock_get_spotify_headers,
    mock_handle_spotify_callback,
)


@pytest.mark.parametrize("expected_output", [USER_DATA_EXAMPLE])
def test_get_current_user_success(
    mock_async_client_get,
    mock_get_spotify_headers,
    test_client,
    expected_output,
):
    mock_async_client_get.return_value = httpx.Response(status_code=200, json=USER_DATA_EXAMPLE)
    response = test_client.get("/user-auth/me")
    assert response.json() == expected_output
    mock_async_client_get.assert_awaited_with(
        "https://api.spotify.com/v1/me",
        headers=SPOTIFY_HEADERS_EXAMPLE,
    )


def test_get_current_user_unauthorized(test_client):
    response = test_client.get("/user-auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert (
        "Access token does not exist in the database, login first to generate one."
        in response.json()["detail"]
    )


def test_get_current_user_failure(mock_async_client_get, mock_get_spotify_headers, test_client):
    mock_async_client_get.side_effect = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="ERROR: Bad request"
    )
    response = test_client.get("/user-auth/me")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "ERROR: Bad request"


def test_login(test_client, mock_generate_spotify_login_url):
    mock_generate_spotify_login_url.return_value = {"login_url": "https://fake-spotify-login.com"}
    response = test_client.get("/user-auth/login")
    assert response.status_code == 200
    assert response.json() == {"login_url": "https://fake-spotify-login.com"}
    mock_generate_spotify_login_url.assert_awaited_once()


def test_callback(test_client, mock_handle_spotify_callback, db_session):
    fake_code = "fake_auth_code"
    mock_handle_spotify_callback.return_value = {"detail": "Spotify callback handled"}
    response = test_client.get(f"/user-auth/callback?code={fake_code}")
    assert response.status_code == 200
    mock_handle_spotify_callback.assert_awaited_once_with(fake_code, db_session)
