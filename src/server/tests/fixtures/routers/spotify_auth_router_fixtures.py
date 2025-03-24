from unittest.mock import AsyncMock, patch
import pytest


@pytest.fixture(scope="function")
def mock_get_spotify_user():
    with patch("app.routers.spotify_auth_router.get_spotify_user") as mock:
        yield mock
