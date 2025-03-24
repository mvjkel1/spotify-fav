from app.db.database import get_db
from app.services.user_auth_service import (
    generate_spotify_login_url,
    get_current_user,
    handle_spotify_callback,
)
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

router = APIRouter(tags=["user_auth"], prefix="/user-auth")


@router.get("/me")
async def get_me(db_session: Session = Depends(get_db)) -> dict:
    """
    Retrieve the current user's information from the database.

    Args:
        db_session (Session): The SQLAlchemy session to interact with the database.

    Returns:
        dict: A dictionary containing the current user's information.
    """
    return await get_current_user(db_session)


@router.get("/login")
async def login() -> dict[str, str]:
    """
    Generate and return the Spotify OAuth2 login URL.

    Returns:
        dict[str, str]: A dictionary containing the Spotify login URL.
    """
    return await generate_spotify_login_url()


@router.get("/callback")
async def callback(request: Request, db_session: Session = Depends(get_db)) -> RedirectResponse:
    """
    Handle the Spotify OAuth2 callback by exchanging the authorization code for access tokens.

    Args:
        request (Request): The FastAPI request object to extract the authorization code.
        db_session (Session): The SQLAlchemy session to interact with the database.

    Returns:
        RedirectResponse: Redirects the user after handling the callback.
    """
    code = request.query_params.get("code")
    return await handle_spotify_callback(code, db_session)
