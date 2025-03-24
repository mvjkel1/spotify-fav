from os import getenv

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException

load_dotenv()

router = APIRouter()


@router.post("/generate_token")
async def generate_token() -> dict:
    """
    Generate Spotify Access Token.

    This endpoint generates a Spotify access token using the provided client credentials.

    Returns:
        dict: The JSON response containing the client access token.

    Raises:
        HTTPException: If the response from Spotify is not successful.
    """
    url = "https://accounts.spotify.com/api/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": getenv("CLIENT_ID"),
        "client_secret": getenv("CLIENT_SECRET"),
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, data=data)
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail=response.text)
