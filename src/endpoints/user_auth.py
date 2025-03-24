import base64
import urllib.parse

import httpx
from dotenv import dotenv_values, find_dotenv
from fastapi import APIRouter, HTTPException, Request

env_path = find_dotenv()
config = dotenv_values(env_path)

router = APIRouter()


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
        "client_id": config["CLIENT_ID"],
        "response_type": "code",
        "redirect_uri": config["REDIRECT_URI"],
        "scope": "user-read-currently-playing user-read-playback-state",
    }
    url = config["SPOTIFY_AUTH_URL"] + "?" + urllib.parse.urlencode(params)
    return {"url": url}


@router.get("/callback")
async def callback(request: Request) -> dict:
    """
    Handle Spotify OAuth2 Callback.

    This endpoint handles the callback from Spotify's OAuth2 process
    and exchanges the authorization code for an access token.

    Args:
        request (Request): The HTTP request containing the authorization code.

    Returns:
        dict: A dictionary containing the access token.

    Raises:
        HTTPException: If the response from Spotify is not successful.
    """
    code = request.query_params.get("code")
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config["REDIRECT_URI"],
        "client_id": config["CLIENT_ID"],
        "client_secret": config["CLIENT_SECRET"],
    }
    encoded_credentials = base64.b64encode(
        f"{config["CLIENT_ID"]}:{config["CLIENT_SECRET"]}".encode()
    ).decode()
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_credentials}",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(config["SPOTIFY_TOKEN_URL"], headers=headers, data=data)
        if response.status_code == 200:
            token_response = response.json()
            return {"access_token": token_response["access_token"]}
        raise HTTPException(status_code=response.status_code, detail=response.text)
