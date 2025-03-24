import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/current_music")
async def current_music(access_token: str) -> dict:
    """
    Fetch Currently Playing Music.

    This endpoint retrieves the currently playing music from the user's Spotify account.

    Args:
        access_token (str): The Spotify access token.

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
async def playback_state(access_token: str) -> dict:
    """
    Fetch Playback State.

    This endpoint retrieves the current playback state from the user's Spotify account.

    Args:
        access_token (str): The Spotify access token.

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


# TODO (when the db is ready)
# @router.get("/compare_timestamp")
# async def compare(access_token: str):
#     response = await playback_state(access_token)
#     if (
#         response["is_playing"]
#         and response["progress_ms"] >= response["item"]["duration_ms"] - 4000
#     ):
#         print("debug")
