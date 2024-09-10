import base64
import urllib.parse

from fastapi.responses import RedirectResponse
import httpx
from dotenv import dotenv_values, find_dotenv
from fastapi import APIRouter, HTTPException, Request

from utils import generate_random_string, get_spotify_headers
from token_manager import token_manager

env_path = find_dotenv()
config = dotenv_values(env_path)

router = APIRouter(tags=["user_auth"])


@router.get("/me")
async def get_current_user() -> dict:
    """
    Fetches the current user's profile from Spotify API.

    Returns:
        dict: Spotify user object as a dictionary.

    Raises:
        HTTPException: If the Spotify API response is unsuccessful.
    """
    url = f"{config['SPOTIFY_API_URL']}/me"
    headers = get_spotify_headers()
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Failed to fetch user data: {response.text}",
        )


async def get_current_user_id() -> str:
    """
    Fetches the Spotify user ID of the current user.

    Args:
        access_token (str): Spotify user access token.

    Returns:
        dict: Spotify user ID.
    """
    user = await get_current_user()
    return user.get("id", "")


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
async def callback(request: Request):
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

        response.raise_for_status()
        response_json = response.json()

        access_token = response_json["access_token"]
        refresh_token = response_json["refresh_token"]

        if not access_token or not refresh_token:
            raise HTTPException(
                status_code=500, detail="Failed to retrieve tokens from Spotify API"
            )

        token_manager.set_tokens(access_token, refresh_token)
        return RedirectResponse(url="http://127.0.0.1:8000/docs")

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code, detail=f"HTTP error occurred: {exc}"
        )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Error while requesting from Spotify: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {exc}")
