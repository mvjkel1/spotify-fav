import pytest
from app.services.user_auth_service import create_refresh_token, get_current_user
from fastapi import HTTPException, status

from ..fixtures.constants import USER_EXAMPLE_DB
from ..fixtures.services.user_auth_service_fixtures import mock_config_env
from ..utils.utils import get_model_attributes


# @pytest.mark.asyncio
# async def test_get_current_user_success(db_session):
#     test_user = USER_EXAMPLE_DB
#     jwt_token = create_refresh_token(data={"sub": test_user.email})
#     db_session.add(test_user)
#     await db_session.commit()
#     result = await get_current_user(jwt_token, db_session)
#     assert get_model_attributes(result) == {
#         "id": 1,
#         "spotify_uid": "1",
#         "hashed_password": "P!w!D",
#         "is_active": True,
#         "email": "user@example.com",
#         "is_polling": False,
#         "last_login": None,
#     }


@pytest.mark.asyncio
async def test_get_current_user_failure(db_session):
    jwt_token = create_refresh_token(data={"sub": "faulty@gmail.com"})
    with pytest.raises(HTTPException) as exc:
        await get_current_user(jwt_token, db_session)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc.value.detail == "Could not validate credentials"
