from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(scope="function")
def mock_generate_spotify_login_url():
    with patch("app.routers.user_auth_router.generate_spotify_login_url") as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_handle_spotify_callback():
    with patch(
        "app.routers.user_auth_router.handle_spotify_callback",
        new_callable=AsyncMock,
    ) as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_get_current_user_router():
    with patch("app.routers.user_auth_router.get_current_user", new_callable=AsyncMock) as mock:
        yield mock
