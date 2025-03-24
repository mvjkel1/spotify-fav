from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db

router = APIRouter()
db_dependency = Annotated[Session, Depends(get_db)]


@router.get("/current_music")
async def current_music(access_token: str) -> dict:
    """
    Fetch Currently Playing Music.

    This endpoint retrieves the currently playing music from the user's Spotify account.

    Args:
        access_token (str): The Spotify user access token.

    Returns:
        dict: The JSON response containing the currently playing music.

    Raises:
        HTTPException: If the response from Spotify is not successful.
    """
    url = "https://api.spotify.com/v1/me/player/currently-playing"
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail=response.text)


@router.get("/playback_state")
async def playback_state(access_token: str):
    """
    Fetch Playback State.

    This endpoint retrieves the current playback state from the user's Spotify account.

    Args:
        access_token (str): The Spotify user access token.

    Returns:
        dict: The JSON response containing the playback state.

    Raises:
        HTTPException: If the response from Spotify is not successful.
    """
    url = "https://api.spotify.com/v1/me/player"
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail=response.text)


# TODO
# async def post_track():
#     pass
