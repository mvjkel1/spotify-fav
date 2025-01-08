from time import time

import pytest
from fastapi import HTTPException, status
from httpx import HTTPStatusError, Request, Response, TimeoutException

from app.db.models import AccessToken
from app.services.token_manager import (
    RefreshTokenError,
    get_spotify_headers,
    get_token_from_db,
    handle_token_refresh,
    is_token_expired,
    refresh_access_token,
    save_token,
)

from ..conftest import db_session
from ..fixtures.services.token_manager_fixtures import (
    expired_token,
    mock_async_client_post,
    mock_config_env,
    mock_get_token,
    mock_refresh_access_token,
    mock_token,
)


@pytest.mark.parametrize(
    "existing_token, access_token, refresh_token, expected_access, expected_refresh",
    [
        (None, "new_access", "new_refresh", "new_access", "new_refresh"),
        ("mock_token", "updated_access", "updated_refresh", "updated_access", "updated_refresh"),
    ],
)
def test_save_token(
    db_session,
    request,
    existing_token,
    access_token,
    refresh_token,
    expected_access,
    expected_refresh,
):
    if existing_token:
        existing_token = request.getfixturevalue(existing_token)
        db_session.add(existing_token)
        db_session.commit()
    save_token(access_token, refresh_token, 3600, db_session)
    token = db_session.query(AccessToken).first()
    assert token.access_token == expected_access
    assert token.refresh_token == expected_refresh
    if not existing_token:
        assert token.expires_at > time()


def test_get_token_from_db_not_found(db_session):
    with pytest.raises(HTTPException) as exc:
        get_token_from_db(db_session)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert (
        exc.value.detail
        == "Access token does not exist in the database, login first to generate one."
    )


@pytest.mark.parametrize(
    "token_fixture, expected_expired",
    [
        ("expired_token", True),
        ("mock_token", False),
    ],
)
def test_is_token_expired(request, token_fixture, expected_expired):
    token_fixture = request.getfixturevalue(token_fixture)
    assert is_token_expired(token_fixture) == expected_expired


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_return_value, side_effect, expected_access, expected_refresh, expected_exception",
    [
        (
            {
                "access_token": "new_access",
                "refresh_token": "new_refresh",
                "expires_at": time() + 3600,
            },
            None,
            "new_access",
            "new_refresh",
            None,
        ),
        (None, RefreshTokenError("Refresh failed"), None, None, HTTPException),
    ],
)
async def test_handle_token_refresh(
    db_session,
    mock_refresh_access_token,
    mock_return_value,
    side_effect,
    expected_access,
    expected_refresh,
    expected_exception,
):
    mock_refresh_access_token.return_value = mock_return_value
    mock_refresh_access_token.side_effect = side_effect
    if expected_exception:
        with pytest.raises(HTTPException) as excinfo:
            await handle_token_refresh("refresh_token", db_session)
        assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert excinfo.value.detail == "Token refresh failed: Refresh failed"
    else:
        new_token = await handle_token_refresh("refresh_token", db_session)
        assert new_token["access_token"] == expected_access
        assert new_token["refresh_token"] == expected_refresh


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_response_data, side_effect, expected_access, expected_exception",
    [
        (
            {"access_token": "new_access", "expires_in": 3600},
            None,
            "new_access",
            None,
        ),
        (
            None,
            HTTPStatusError(
                message="HTTP error",
                request=None,
                response=Response(
                    status_code=status.HTTP_400_BAD_REQUEST, text="Invalid refresh token"
                ),
            ),
            None,
            RefreshTokenError,
        ),
        (None, TimeoutException("Request timeout"), None, RefreshTokenError),
    ],
)
async def test_refresh_access_token(
    db_session,
    mock_async_client_post,
    mock_response_data,
    side_effect,
    expected_access,
    expected_exception,
):
    mock_request = Request("POST", "mock_request")
    mock_async_client_post.return_value = Response(
        status_code=status.HTTP_200_OK, json=mock_response_data, request=mock_request
    )
    mock_async_client_post.side_effect = side_effect
    if expected_exception:
        with pytest.raises(RefreshTokenError):
            await refresh_access_token("refresh_token", db_session)
    else:
        new_token = await refresh_access_token("refresh_token", db_session)
        assert new_token["access_token"] == expected_access
        assert new_token["refresh_token"] == "refresh_token"


@pytest.mark.asyncio
async def test_get_spotify_headers(mock_get_token, db_session):
    mock_get_token.return_value = {
        "access_token": "valid_access",
        "refresh_token": "refresh_token",
        "expires_at": time() + 3600,
    }
    headers = await get_spotify_headers(db_session)
    assert headers["Authorization"] == "Bearer valid_access"
    assert headers["Content-Type"] == "application/json"
