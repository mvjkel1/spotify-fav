from typing import Annotated

from app.db.database import async_get_db
from app.db.schemas import TokenSchema, UserRegister, UserSchema
from app.services.user_auth_service import (
    generate_tokens,
    get_current_active_user,
    handle_user_register,
    refresh_access_token,
)
from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio.session import AsyncSession

router = APIRouter(tags=["user-auth"], prefix="/user-auth")


@router.post("/register")
async def register_user(user: UserRegister, db_session: AsyncSession = Depends(async_get_db)):
    """
    Handles user registration by calling the `handle_user_register` function. If the registration is successful,
    a new user is created in the database.

    Args:
        user (UserRegister): The user registration data, including email and password.
        db_session (AsyncSession): The database session, injected by FastAPI.

    Returns:
        dict: A dictionary containing a success message and the email of the newly registered user.
    """
    return await handle_user_register(user, db_session)


@router.post("/token")
async def generate_user_auth_tokens(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    response: Response,
    db_session: AsyncSession = Depends(async_get_db),
):
    """
    Generate an access and refresh tokens for the user.

    Args:
        form_data (OAuth2PasswordRequestForm): The user's username and password provided in the form.
        response (Response): The response object, used to set the access and refresh tokens as a cookies.
        db_session (AsyncSession): The SQLAlchemy session used to interact with the database.

    Returns:
        TokenSchema: The generated access token and its type.
    """
    access_token, _ = await generate_tokens(form_data, response, db_session)
    return TokenSchema(access_token=access_token, token_type="Bearer")


@router.post("/refresh-token")
async def refresh_user_access_token(
    current_user: Annotated[UserSchema, Depends(get_current_active_user)],
    request: Request,
    response: Response,
    db_session: AsyncSession = Depends(async_get_db),
) -> TokenSchema:
    """
    Refresh the access token using the refresh token.
    """
    return await refresh_access_token(request, response, db_session)


@router.post("/login")
async def login_user(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    response: Response,
    db_session: AsyncSession = Depends(async_get_db),
) -> dict[str, str]:
    """
    Log in the user by generating an access token.

    Args:
        form_data (OAuth2PasswordRequestForm): The user's username and password provided in the form.
        response (Response): The response object, used to set the access token as a cookie.
        db_session (AsyncSession): The SQLAlchemy session used to interact with the database.

    Returns:
        dict: A dictionary with a message indicating the login was successful.
    """
    await generate_user_auth_tokens(form_data, response, db_session)
    return {"message": "Login successful"}


@router.get("/users/me/", response_model=UserSchema)
async def read_users_me(
    current_user: Annotated[UserSchema, Depends(get_current_active_user)],
) -> UserSchema:
    """
    Retrieve the current user's information.

    Args:
        current_user (UserSchema): The currently authenticated user, provided by the dependency `get_current_active_user`.

    Returns:
        UserSchema: A schema containing the user's information.
    """
    return current_user
