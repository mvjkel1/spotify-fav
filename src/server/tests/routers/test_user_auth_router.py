import pytest
from app.db.models import User
from fastapi import status
from sqlalchemy import select
from tests.utils.utils import are_tokens_valid, extract_tokens

from ..conftest import db_session, test_client
from ..fixtures.routers.user_auth_router_fixtures import (
    mock_config_env as user_auth_router_fixtures,
)
from ..fixtures.services.user_auth_service_fixtures import (
    mock_config_env as user_auth_service_fixtures,
)

PATH = "/user-auth"


@pytest.mark.asyncio
async def test_register_user_success(test_client, db_session):
    payload = {"email": "test@example.com", "password": "securepassword123"}
    response = await test_client.post(f"{PATH}/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    response_data = response.json()
    assert response_data["message"] == "User registered successfully"
    assert response_data["email"] == payload["email"]
    result = await db_session.execute(select(User).filter_by(email=payload["email"]))
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.email == payload["email"]


@pytest.mark.asyncio
async def test_register_user_missing_password(test_client):
    payload = {"email": "test@example.com"}
    response = await test_client.post(f"{PATH}/register", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_register_user_invalid_email(test_client):
    payload = {"email": "invalid-email", "password": "securepassword123"}
    response = await test_client.post(f"{PATH}/register", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_register_user_duplicate_email(test_client, db_session):
    payload = {"email": "duplicate@example.com", "password": "securepassword123"}
    await test_client.post(f"{PATH}/register", json=payload)
    response = await test_client.post(f"{PATH}/register", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_login_user_success(test_client, db_session):
    register_payload = {"email": "test@example.com", "password": "securepassword123"}
    await test_client.post(f"{PATH}/register", json=register_payload)
    login_payload = {"username": "test@example.com", "password": "securepassword123"}
    response = await test_client.post(f"{PATH}/login", data=login_payload)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["message"] == "Login successful"


@pytest.mark.asyncio
async def test_login_user_invalid_credentials(test_client):
    login_payload = {"username": "nonexistent@example.com", "password": "wrongpassword"}
    response = await test_client.post(f"{PATH}/login", data=login_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_login_user_missing_password(test_client):
    login_payload = {"username": "test@example.com"}
    response = await test_client.post(f"{PATH}/login", data=login_payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_login_user_missing_username(test_client):
    login_payload = {"password": "securepassword123"}
    response = await test_client.post(f"{PATH}/login", data=login_payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_login_user_nonexistent_email(test_client, db_session):
    register_payload = {"email": "test@example.com", "password": "securepassword123"}
    await test_client.post(f"{PATH}/register", json=register_payload)
    login_payload = {"username": "nonexistent@example.com", "password": "securepassword123"}
    response = await test_client.post(f"{PATH}/login", data=login_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_login_user_success_with_tokens_in_cookies(test_client, db_session):
    register_payload = {"email": "test@example.com", "password": "securepassword123"}
    await test_client.post(f"{PATH}/register", json=register_payload)
    login_payload = {"username": "test@example.com", "password": "securepassword123"}
    response = await test_client.post(f"{PATH}/login", data=login_payload)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["message"] == "Login successful"
    headers = str(response.headers)
    assert are_tokens_valid(*extract_tokens(headers)) is True


@pytest.mark.asyncio
async def test_login_user_success_after_multiple_attempts(test_client, db_session):
    register_payload = {"email": "test@example.com", "password": "securepassword123"}
    await test_client.post(f"{PATH}/register", json=register_payload)
    login_payload = {"username": "test@example.com", "password": "securepassword123"}
    for _ in range(3):
        response = await test_client.post(f"{PATH}/login", data=login_payload)
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["message"] == "Login successful"
        headers = str(response.headers)
        assert are_tokens_valid(*extract_tokens(headers)) is True
