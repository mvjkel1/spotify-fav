from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(scope="function")
def mock_get_current_user_router():
    with patch("app.routers.user_auth_router.get_current_user", new_callable=AsyncMock) as mock:
        yield mock
