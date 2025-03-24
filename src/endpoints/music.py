import asyncio
import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from models import Track
from database import SessionLocal
from sqlalchemy.exc import SQLAlchemyError
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


async def poll_playback_state(access_token: str, db_session: Session):
    """
    Polls the playback state and updates the database with the current track information.

    Args:
        access_token (str): Spotify user access token.
        db_session (Session): Database session for interacting with the database.
    """
    while True:
        try:
            state = await playback_state(access_token)
            progress_ms = state["progress_ms"]
            duration_ms = state["item"]["duration_ms"]
            listened = (duration_ms - progress_ms) < 15000

            track_title = state["item"]["name"]
            track_exists = db_session.query(Track).filter(Track.title == track_title).first()

            if state["is_playing"] and listened and not track_exists:
                track_model = Track(title=track_title)
                db_session.add(track_model)
                db_session.commit()

        except HTTPException as e:
            print(f"Error fetching playback state: {e.detail}")

        except SQLAlchemyError as db_error:
            print(f"Database error: {str(db_error)}")
            db_session.rollback()

        except Exception as e:
            print(f"Unexpected error: {str(e)}")

        await asyncio.sleep(5)


@router.post("/track")
async def track(
    background_tasks: BackgroundTasks,
    access_token: str,
    db: Session = Depends(get_db),
):
    """
    Start background task to poll playback state.

    Args:
        background_tasks (BackgroundTasks): FastAPI's background task manager.
        access_token (str): Spotify user access token.
        db (Session): Database session.

    Returns:
        dict: Confirmation message.
    """
    background_tasks.add_task(poll_playback_state, access_token, db)
    return {"message": "Playback state polling started in the background."}
