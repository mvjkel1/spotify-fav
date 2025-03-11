import pytest
from fastapi import status

from tests.fixtures.constants import USER_DATA_EXAMPLE
from tests.fixtures.routers.spotify_auth_router_fixtures import mock_get_spotify_user
from ..conftest import db_session, test_client

PATH = "/spotify-auth"


@pytest.mark.asyncio
async def test_get_me(db_session, test_client, mock_get_spotify_user):
    mock_get_spotify_user.return_value = USER_DATA_EXAMPLE
    response = await test_client.get(f"{PATH}/me")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == USER_DATA_EXAMPLE
