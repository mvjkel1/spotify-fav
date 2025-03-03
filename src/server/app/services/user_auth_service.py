import base64
import urllib.parse

import httpx
from app.token_manager import parse_token_response, save_token
from app.utils import generate_random_string, get_spotify_headers
from dotenv import dotenv_values, find_dotenv
from fastapi import HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

env_path = find_dotenv()
config = dotenv_values(env_path)


async def get_current_user(db_session: Session) -> dict:
    """
    Retrieve the current user's Spotify profile information.

    Args:
        db_session (Session): SQLAlchemy session to get Spotify headers.

    Returns:
        dict: A dictionary containing the current user's profile information.
    """
    url = f"{config['SPOTIFY_API_URL']}/me"
    headers = await get_spotify_headers(db_session)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == status.HTTP_200_OK:
            return response.json()
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Failed to fetch user data: {response.text}",
        )


async def get_current_user_id(db_session: Session) -> str:
    """
    Retrieve the current user's Spotify user ID.

    Args:
        db_session (Session): SQLAlchemy session to get Spotify headers.

    Returns:
        str: The current user's Spotify user ID.
    """
    current_user = await get_current_user(db_session)
    current_user_id = current_user.get("id")
    if not current_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to fetch current user ID",
        )
    return current_user_id


async def generate_spotify_login_url() -> dict:
    """
    Generate the Spotify OAuth2 login URL.

    Returns:
        dict: A dictionary containing the login URL for Spotify OAuth2 authorization.
    """
    params = {
        "response_type": "code",
        "client_id": config["CLIENT_ID"],
        "scope": config["SPOTIFY_API_SCOPES"],
        "redirect_uri": config["REDIRECT_URI"],
        "state": generate_random_string(16),
    }
    url = config["SPOTIFY_AUTH_URL"] + "?" + urllib.parse.urlencode(params)
    return {"login_url": url}


async def handle_spotify_callback(code: str, db_session: Session) -> RedirectResponse:
    """
    Handle the Spotify OAuth2 callback and exchange the authorization code for access and refresh tokens.

    Args:
        code (str): Authorization code from Spotify.
        db_session (Session): SQLAlchemy session for token storage.

    Returns:
        RedirectResponse: Redirect to the provided redirect URL after successful authentication.
    """
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Authorization code missing"
        )
    auth_header = base64.b64encode(
        f"{config['CLIENT_ID']}:{config['CLIENT_SECRET']}".encode()
    ).decode()
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {auth_header}",
    }
    form_data = {
        "code": code,
        "redirect_uri": config["REDIRECT_URI"],
        "grant_type": "authorization_code",
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(config["SPOTIFY_TOKEN_URL"], data=form_data, headers=headers)
        response.raise_for_status()
        tokens = parse_token_response(response)
        access_token, refresh_token, expires_in = tokens.get("access_token"), tokens.get("refresh_token"), tokens.get("expires_in")
        if not access_token or not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve tokens from Spotify"
            )
        save_token(access_token, refresh_token, expires_in, db_session)
        return RedirectResponse(url=config["CALLBACK_REDIRECT_URL"])
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        status_code = getattr(exc.response, "status_code", status.HTTP_502_BAD_GATEWAY)
        raise HTTPException(
            status_code=status_code, detail=f"Error occurred: {exc}"
        ) from exc
