from unittest.mock import patch

import pytest

from ..constants import ENV_CONFIG_EXAMPLE, SPOTIFY_HEADERS_EXAMPLE


@pytest.fixture(scope="module", autouse=True)
def mock_config_env():
    with patch(
        "app.services.user_auth_service.config",
        ENV_CONFIG_EXAMPLE,
    ) as mock:
        yield mock
