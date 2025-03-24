from typing import Annotated
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from jose import jwt
from sqlalchemy.ext.asyncio.session import AsyncSession

from app.db.database import async_get_db
from app.services.spotify_auth_service import (
    generate_spotify_login_url,
    get_spotify_user,
    handle_spotify_callback,
)
from app.db.schemas import UserSchema
from app.services.user_auth_service import get_current_active_user
from app.services.utils import config, get_jwt_token

router = APIRouter(tags=["spotify-auth"], prefix="/spotify-auth")


@router.get("/me")
async def get_me(
    current_user: Annotated[UserSchema, Depends(get_current_active_user)],
    db_session: AsyncSession = Depends(async_get_db),
) -> dict:
    """
    Retrieve the current Spotify user's information from the database.

    Args:
        current_user (UserSchema): The current authenticated user, provided by the dependency get_current_active_user.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.

    Returns:
        dict: A dictionary containing the current user's information.
    """
    return await get_spotify_user(current_user.id, db_session)


@router.get("/login")
async def login_spotify(
    current_user: Annotated[UserSchema, Depends(get_current_active_user)],
    jwt_token: str = Depends(get_jwt_token),
) -> dict[str, str]:
    """
    Generate and return the Spotify OAuth2 login URL.

    Args:
        current_user (UserSchema): The currently authenticated user, provided by the dependency get_current_active_user.
        jwt_token (str): The JWT token used to authenticate the request and obtain Spotify access.

    Returns:
        dict[str, str]: A dictionary containing the Spotify login URL.
    """
    return generate_spotify_login_url(jwt_token)


@router.get("/callback")
async def callback(
    request: Request, db_session: AsyncSession = Depends(async_get_db)
) -> RedirectResponse:
    """
    Handle the Spotify OAuth2 callback by exchanging the authorization code for access tokens.

    Args:
        request (Request): The FastAPI request object to extract the authorization code.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.

    Returns:
        RedirectResponse: Redirects the user after handling the callback.
    """
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if not state:
        raise ValueError("State parameter is missing")
    decoded_payload = jwt.decode(state, config["SECRET_KEY"], algorithms=config["ALGORITHM"])
    jwt_token = decoded_payload["jwt_token"]
    return await handle_spotify_callback(code, jwt_token, db_session)
