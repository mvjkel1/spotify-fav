from unittest.mock import patch
import pytest
from ..utils.utils import SPOTIFY_HEADERS_EXAMPLE


@pytest.fixture
def mock_get_spotify_headers():
    with patch(
        "app.services.user_auth_service.get_spotify_headers",
        return_value=SPOTIFY_HEADERS_EXAMPLE,
    ) as mock:
        yield mock


@pytest.fixture
def mock_async_client_get():
    with patch(
        "app.services.user_auth_service.httpx.AsyncClient.get",
    ) as mock:
        yield mock


@pytest.fixture
def mock_get_current_user():
    with patch("app.services.user_auth_service.get_current_user") as mock:
        yield mock
