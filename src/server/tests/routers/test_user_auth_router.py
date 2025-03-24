import pytest
from fastapi import HTTPException, status

from ..conftest import db_session, test_client
from ..fixtures.constants import USER_DATA_EXAMPLE
from ..fixtures.user_auth_fixtures import (
    mock_generate_spotify_login_url,
    mock_handle_spotify_callback,
    mock_config_env,
    mock_get_current_user_router,
)


@pytest.mark.parametrize(
    "mock_return_value, mock_side_effect, expected_status, expected_response",
    [
        (
            USER_DATA_EXAMPLE,
            None,
            status.HTTP_200_OK,
            USER_DATA_EXAMPLE,
        ),
        (
            None,
            HTTPException(status.HTTP_400_BAD_REQUEST, detail="ERROR: Bad request"),
            status.HTTP_400_BAD_REQUEST,
            {"detail": "ERROR: Bad request"},
        ),
    ],
)
def test_get_current_user(
    test_client,
    db_session,
    mock_get_current_user_router,
    mock_return_value,
    mock_side_effect,
    expected_status,
    expected_response,
):
    mock_get_current_user_router.return_value = mock_return_value
    mock_get_current_user_router.side_effect = mock_side_effect
    response = test_client.get("/user-auth/me")
    assert response.status_code == expected_status
    assert response.json() == expected_response
    mock_get_current_user_router.assert_awaited_with(db_session)


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
