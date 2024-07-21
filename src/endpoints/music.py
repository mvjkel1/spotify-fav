import httpx
from fastapi import APIRouter, Depends, HTTPException
from models import Track
from database import SessionLocal
from sqlalchemy.orm import Session

router = APIRouter(prefix="/music", tags=["music"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
# @router.post("/track")
# async def track(db: Session = Depends(get_db)):
#     track_model = Track()
#     track_model.spotify_id = "123"
#     track_model.title = "test_title"
#     track_model.listened = True
#     db.add(track_model)
#     db.commit()
