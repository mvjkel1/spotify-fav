from unittest.mock import patch

import httpx
import pytest
from fastapi import HTTPException, status
from ..fixtures.user_auth_fixtures import (
    mock_async_client_get,
    mock_get_spotify_headers,
)

from ..utils.utils import SPOTIFY_HEADERS_EXAMPLE, USER_DATA_EXAMPLE


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
def test_get_current_user_unauthorized(mock_get_spotify_headers, test_client, expected_response):
    response = test_client.get("/user-auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == expected_response


def test_get_current_user_failure(mock_async_client_get, mock_get_spotify_headers, test_client):
    mock_async_client_get.side_effect = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="ERROR: Bad request"
    )
    response = test_client.get("/user-auth/me")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "ERROR: Bad request"
