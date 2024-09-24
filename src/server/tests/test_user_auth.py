from unittest.mock import patch

import httpx
import pytest
import status
from app.endpoints.user_auth import get_current_user_id
from fastapi import HTTPException

from .utils.utils import (SPOTIFY_HEADERS_EXAMPLE, USER_DATA_EXAMPLE,
                          USER_DATA_EXAMPLE_MALFORMED)

USER_DATA = {
    "id": "user123",
    "display_name": "Test User",
    "email": "testuser@example.com",
}


@pytest.fixture
def mock_get_spotify_headers():
    with patch(
        "app.endpoints.user_auth.get_spotify_headers",
        return_value=SPOTIFY_HEADERS_EXAMPLE,
    ) as mock:
        yield mock


@pytest.fixture
def mock_async_client_get():
    with patch(
        "app.endpoints.user_auth.httpx.AsyncClient.get",
    ) as mock:
        yield mock


@pytest.fixture
def mock_get_current_user():
    with patch("app.endpoints.user_auth.get_current_user") as mock:
        yield mock


@pytest.mark.parametrize("expected_output", [USER_DATA])
def test_get_current_user_success(
    mock_async_client_get,
    mock_get_spotify_headers,
    test_client,
    expected_output,
):
    mock_async_client_get.return_value = httpx.Response(
        status_code=200, json=USER_DATA_EXAMPLE
    )
    response = test_client.get("/user-auth/me")
    assert response.json() == expected_output
    mock_async_client_get.assert_called_once_with(
        "https://api.spotify.com/v1/me",
        headers=SPOTIFY_HEADERS_EXAMPLE,
    )


@pytest.mark.parametrize(
    "expected_response",
    [
        {
            "detail": (
                "Failed to fetch user data: {\n"
                '  "error": {\n'
                '    "status": 401,\n'
                '    "message": "Invalid access token"\n'
                "  }\n}"
            )
        },
    ],
)
def test_get_current_user_unauthorized(
    mock_get_spotify_headers, test_client, expected_response
):
    response = test_client.get("/user-auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == expected_response


def test_get_current_user_failure(
    mock_async_client_get, mock_get_spotify_headers, test_client
):
    mock_async_client_get.side_effect = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="ERROR: Bad request"
    )
    response = test_client.get("/user-auth/me")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "ERROR: Bad request"


@pytest.mark.asyncio
async def test_get_current_user_id_success(mock_get_current_user, db_session):
    mock_get_current_user.return_value = USER_DATA_EXAMPLE
    response = await get_current_user_id(db_session)
    assert response == "user123"


@pytest.mark.asyncio
async def test_get_current_user_id_failure(mock_get_current_user, db_session):
    mock_get_current_user.return_value = USER_DATA_EXAMPLE_MALFORMED
    response = await get_current_user_id(db_session)
    assert response == ""
