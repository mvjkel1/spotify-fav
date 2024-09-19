import base64
import urllib.parse

import httpx
from dotenv import dotenv_values, find_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.token_manager import save_token
from app.utils import generate_random_string, get_spotify_headers

env_path = find_dotenv()
config = dotenv_values(env_path)
router = APIRouter(tags=["user_auth"])


@router.get("/me")
async def get_current_user(db_session: Session = Depends(get_db)) -> dict:
    """
    Retrieve the current user's Spotify profile information.

    This endpoint uses the Spotify API to fetch the current user's profile data.
    It requires a valid access token to authenticate the request.

    Args:
        db_session (Session): The database session dependency, used for obtaining headers.

    Returns:
        dict: A dictionary containing the current user's profile information.

    Raises:
        HTTPException: If the request to the Spotify API fails, an HTTPException is raised
        with the appropriate status code and error details.
    """
    url = f"{config['SPOTIFY_API_URL']}/me"
    headers = await get_spotify_headers(db_session)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Failed to fetch user data: {response.text}",
        )


async def get_current_user_id(db_session: Session) -> str:
    """
    Retrieve the current user's Spotify user ID.

    This function uses the `get_current_user` function to fetch the current user's profile
    data and extracts the user ID from the response.

    Args:
        db_session (Session): The database session dependency.

    Returns:
        str: The current user's Spotify user ID.
    """
    current_user = await get_current_user(db_session=db_session)
    return current_user["id"]


@router.get("/login")
async def login() -> dict:
    """
    Generate Spotify OAuth2 login URL.

    This endpoint creates a URL that redirects the user to Spotify's authorization page
    where they can grant the application access to their Spotify account.

    Returns:
        dict: A dictionary containing the URL for the user to log in via Spotify.
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


@router.get("/callback")
async def callback(request: Request, db_session: Session = Depends(get_db)):
    """
    Handle the Spotify OAuth2 callback.

    This endpoint exchanges the authorization code received from Spotify for access and
    refresh tokens, then saves them. It also handles errors that may occur during this process.

    Args:
        request (Request): The request object containing the authorization code.
        db_session (Session): The database session dependency.

    Returns:
        RedirectResponse: Redirects the user to the documentation page upon successful token exchange.

    Raises:
        HTTPException: If any error occurs during the token exchange process or if the authorization
        code is missing, an HTTPException is raised with the appropriate status code and error details.
    """
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not found in request")
    try:
        auth_header = base64.b64encode(
            f"{config['CLIENT_ID']}:{config['CLIENT_SECRET']}".encode()
        ).decode()
        token_url = config["SPOTIFY_TOKEN_URL"]
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth_header}",
        }
        form_data = {
            "code": code,
            "redirect_uri": config["REDIRECT_URI"],
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=form_data, headers=headers)
        response_json = response.json()
        access_token = response_json["access_token"]
        refresh_token = response_json["refresh_token"]
        expires_in = response_json["expires_in"]
        if not access_token or not refresh_token:
            raise HTTPException(
                status_code=500, detail="Failed to retrieve tokens from Spotify API"
            )
        save_token(access_token, refresh_token, expires_in, db_session)
        return RedirectResponse(url=config["CALLBACK_REDIRECT_URL"])
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code, detail=f"HTTP error occurred: {exc}"
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502, detail=f"Error while requesting from Spotify: {exc}"
        ) from exc
