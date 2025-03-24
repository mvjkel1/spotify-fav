import httpx
from dotenv import dotenv_values, find_dotenv
from fastapi import APIRouter, HTTPException

env_path = find_dotenv()
config = dotenv_values(env_path)

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
        "client_id": config["CLIENT_ID"],
        "client_secret": config["CLIENT_SECRET"],
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, data=data)
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail=response.text)
