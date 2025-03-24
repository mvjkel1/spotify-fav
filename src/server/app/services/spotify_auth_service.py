import base64
import urllib.parse

import httpx
from app.services.spotify_token_manager import (
    get_spotify_headers,
    save_spotify_token,
)
from app.services.user_auth_service import get_current_user
from app.services.utils import config
from fastapi import HTTPException, status
from fastapi.responses import RedirectResponse
from jose import jwt
from sqlalchemy.ext.asyncio.session import AsyncSession


async def get_spotify_user(user_id: int, db_session: AsyncSession) -> dict:
    """
    Retrieve the current user's Spotify profile information.

    Args:
        user_id (int): The ID of logged in user.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.

    Returns:
        dict: A dictionary containing the current user's profile information.
    """
    url = f"{config['SPOTIFY_API_URL']}/me"
    async with httpx.AsyncClient() as client:
        spotify_headers = await get_spotify_headers(user_id, db_session)
        response = await client.get(url, headers=spotify_headers)
        response.raise_for_status()
        return response.json()


async def get_current_spotify_user_id(user_id: int, db_session: AsyncSession) -> str:
    """
    Retrieve the current user's Spotify user ID.

    Args:
        user_id (int): The ID of logged in user.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.

    Returns:
        str: The current user's Spotify user ID.

    Raises:
        HTTPException: If the user ID is missing or cannot be retrieved.
    """
    spotify_user = await get_spotify_user(user_id, db_session)
    spotify_user_id = spotify_user.get("id")
    if not spotify_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to fetch current user ID",
        )
    return spotify_user_id


def generate_spotify_login_url(jwt_token: str) -> dict[str, str]:
    """
    Generate the Spotify OAuth2 login URL.

    Args:
        jwt_token (str): The JWT token used to authenticate the request and obtain Spotify access.

    Returns:
        dict[str, str]: A dictionary containing the login URL for Spotify OAuth2 authorization.
    """
    payload = {
        "jwt_token": jwt_token,
    }
    encoded_jwt = jwt.encode(payload, config["SECRET_KEY"], algorithm=config["ALGORITHM"])
    params = {
        "response_type": "code",
        "client_id": config["CLIENT_ID"],
        "scope": config["SPOTIFY_API_SCOPES"],
        "redirect_uri": config["REDIRECT_URI"],
        "state": encoded_jwt,
    }
    url = config["SPOTIFY_AUTH_URL"] + "?" + urllib.parse.urlencode(params)
    return {"login_url": url}


async def handle_spotify_callback(
    code: str, jwt_token: str, db_session: AsyncSession
) -> RedirectResponse:
    """
    Handle the callback from Spotify after user authorization.

    Args:
        code (str): The authorization code returned from Spotify.
        jwt_token (str): The JWT token used to authenticate the Spotify API request.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.

    Returns:
        RedirectResponse: Redirect to a specified URL after successful token retrieval.

    Raises:
        HTTPException: If the authorization code is missing or token retrieval fails.
    """
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Authorization code missing"
        )
    headers = build_spotify_auth_headers()
    form_data = build_spotify_token_request_data(code)
    tokens = await exchange_token_with_spotify(form_data, headers)
    access_token, refresh_token, expires_in = map(
        tokens.get, ["access_token", "refresh_token", "expires_in"]
    )
    if not access_token or not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tokens from Spotify",
        )
    current_user = await get_current_user(jwt_token, db_session)
    await save_spotify_token(access_token, refresh_token, expires_in, current_user.id, db_session)
    spotify_user = await get_spotify_user(current_user.id, db_session)
    current_user.spotify_uid = spotify_user.get("id")
    await db_session.commit()
    return RedirectResponse(url=config["CALLBACK_REDIRECT_URL"])


def build_spotify_auth_headers() -> dict[str, str]:
    """
    Build the authorization headers required for token exchange with Spotify.

    Returns:
        dict[str, str]: A dictionary containing the necessary authorization headers.
    """
    auth_header = base64.b64encode(
        f"{config['CLIENT_ID']}:{config['CLIENT_SECRET']}".encode()
    ).decode()
    return {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {auth_header}",
    }


def build_spotify_token_request_data(code: str) -> dict[str, str]:
    """
    Build the form data for exchanging the authorization code for tokens.

    Args:
        code (str): The authorization code received from Spotify.

    Returns:
        dict[str, str]: A dictionary containing the form data for token exchange.
    """
    return {
        "code": code,
        "redirect_uri": config["REDIRECT_URI"],
        "grant_type": "authorization_code",
    }


async def exchange_token_with_spotify(form_data: dict, headers: dict) -> dict[str, str]:
    """
    Exchange the authorization code with Spotify for access and refresh tokens.

    Args:
        form_data (dict): The form data for token exchange.
        headers (dict): The authorization headers.

    Returns:
        dict[str, str]: A dictionary containing the tokens from Spotify.

    Raises:
        HTTPException: If an error occurs during the HTTP request.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                config["SPOTIFY_TOKEN_URL"], data=form_data, headers=headers
            )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code, detail=f"HTTP error occurred: {exc}"
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Network error occurred: {exc}"
        ) from exc
