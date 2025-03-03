import base64
import urllib.parse

import httpx
from app.token_manager import get_token_from_db, save_token
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

    Raises:
        HTTPException: If the user data cannot be retrieved from Spotify.
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

    Raises:
        HTTPException: If the user ID is missing or cannot be retrieved.
    """
    current_user = await get_current_user(db_session)
    current_user_id = current_user.get("id")
    if not current_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to fetch current user ID",
        )
    return current_user_id


async def generate_spotify_login_url() -> dict[str, str]:
    """
    Generate the Spotify OAuth2 login URL.

    Returns:
        dict[str, str]: A dictionary containing the login URL for Spotify OAuth2 authorization.
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
    Handle the callback from Spotify after user authorization.

    Args:
        code (str): The authorization code returned from Spotify.
        db_session (Session): SQLAlchemy session for token saving.

    Returns:
        RedirectResponse: Redirect to a specified URL after successful token retrieval.

    Raises:
        HTTPException: If the authorization code is missing or token retrieval fails.
    """
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Authorization code missing"
        )
    headers = build_auth_headers()
    form_data = build_token_request_data(code)
    tokens = await exchange_token_with_spotify(form_data, headers)
    access_token, refresh_token, expires_in = map(
        tokens.get, ["access_token", "refresh_token", "expires_in"]
    )
    if not access_token or not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tokens from Spotify",
        )
    save_token(access_token, refresh_token, expires_in, db_session)
    return RedirectResponse(url=config["CALLBACK_REDIRECT_URL"])


def build_auth_headers() -> dict[str, str]:
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


def build_token_request_data(code: str) -> dict[str, str]:
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
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code, detail=f"HTTP error occurred: {exc}"
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Network error occurred: {exc}"
        ) from exc
    return response.json()


def is_user_authorized(db_session: Session) -> bool:
    """
    Check if the user is authorized based on the presence of a token in the database.

    Args:
        db_session (Session): The current database session.

    Returns:
        bool: True if user is authorized, False otherwise.
    """
    try:
        get_token_from_db(db_session)
    except HTTPException:
        return False
    return True
