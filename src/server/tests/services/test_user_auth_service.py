import pytest
from fastapi import HTTPException, status
from ..utils.utils import USER_DATA_EXAMPLE, USER_DATA_EXAMPLE_MALFORMED
from app.services.user_auth_service import get_current_user_id
from ..routers.test_user_auth_router import mock_get_current_user
from ..conftest import db_session


@pytest.mark.asyncio
async def test_get_current_user_id_success(mock_get_current_user, db_session):
    mock_get_current_user.return_value = USER_DATA_EXAMPLE
    response = await get_current_user_id(db_session)
    assert response == "user123"


@pytest.mark.asyncio
async def test_get_current_user_id_failure(mock_get_current_user, db_session):
    mock_get_current_user.return_value = USER_DATA_EXAMPLE_MALFORMED
    with pytest.raises(HTTPException) as exc:
        await get_current_user_id(db_session)
    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == "Failed to fetch current user ID"
