import urllib.parse
from os import getenv

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request

from models import TokenRequest

load_dotenv()

router = APIRouter()


@router.post("/generate_token")
async def generate_token(request: TokenRequest) -> dict:
    """
    Generate Spotify Access Token.

    This endpoint generates a Spotify access token using the provided client credentials.

    Args:
        request (TokenRequest): The request body containing client_id and client_secret.

    Returns:
        dict: The JSON response containing the access token.

    Raises:
        HTTPException: If the response from Spotify is not successful.
    """
    url = "https://accounts.spotify.com/api/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": request.client_id,
        "client_secret": request.client_secret,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, data=data)
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail=response.text)


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
        "client_id": getenv("CLIENT_ID"),
        "response_type": "code",
        "redirect_uri": getenv("REDIRECT_URI"),
        "scope": "user-read-currently-playing user-read-playback-state",
    }
    url = getenv("SPOTIFY_AUTH_URL") + "?" + urllib.parse.urlencode(params)
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
        "redirect_uri": getenv("REDIRECT_URI"),
        "client_id": getenv("CLIENT_ID"),
        "client_secret": getenv("CLIENT_SECRET"),
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            getenv("SPOTIFY_TOKEN_URL"), headers=headers, data=data
        )
        if response.status_code == 200:
            token_response = response.json()
            return {"access_token": token_response["access_token"]}
        raise HTTPException(status_code=response.status_code, detail=response.text)


async def get_access_token(client_id: str, client_secret: str) -> str:
    """
    Retrieve Spotify Access Token.

    Args:
        client_id (str): The Spotify client ID.
        client_secret (str): The Spotify client secret.

    Returns:
        str: The Spotify access token.
    """
    token_request = TokenRequest(client_id=client_id, client_secret=client_secret)
    token_response = await generate_token(token_request)
    return token_response["access_token"]
