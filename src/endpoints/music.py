import asyncio
from hashlib import sha256
import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from models import Track
from database import SessionLocal
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

router = APIRouter(tags=["music"])


def get_db():
    """
    Provides a database session to be used as a dependency.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/current_music")
async def current_music(access_token: str) -> dict:
    """
    Fetch the currently playing music from the user's Spotify account.

    Args:
        access_token (str): Spotify user access token.

    Returns:
        dict: JSON response with the currently playing music.

    Raises:
        HTTPException: If the Spotify API response is unsuccessful.
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
    Fetch the current playback state from the user's Spotify account.

    Args:
        access_token (str): Spotify user access token.

    Returns:
        dict: JSON response with the playback state.

    Raises:
        HTTPException: If the Spotify API response is unsuccessful.
    """
    url = "https://api.spotify.com/v1/me/player"
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail=response.text)


async def poll_playback_state(access_token: str, db_session: Session) -> None:
    """
    Continuously poll the playback state and update the database with the current track information.

    Args:
        access_token (str): Spotify user access token.
        db_session (Session): SQLAlchemy database session.
    """
    current_track_id = None
    while True:
        try:
            state = await playback_state(access_token)
            track_id = state["item"]["id"]
            if track_id != current_track_id:
                current_track_id = track_id
            await handle_playing_track(state, db_session, access_token)
        except HTTPException as error:
            print(f"Error fetching playback state: {error}")
        except SQLAlchemyError as error:
            print(f"Database error: {error}")
        except Exception as error:
            print(f"Unexpected error: {error}")
        await asyncio.sleep(1)

        except HTTPException as e:
            print(f"Error fetching playback state: {e.detail}")

async def handle_playing_track(
    state: dict, db_session: Session, access_token: str
) -> None:
    """
    Handle the logic for a track that is currently playing.

    Args:
        state (dict): Current playback state.
        db_session (Session): SQLAlchemy database session.
        access_token (str): Spotify user access token.
    """
    progress, duration = state["progress_ms"], state["item"]["duration_ms"]
    track_title = state["item"]["name"]
    ten_seconds_passed = progress >= 10000
    ten_seconds_left = (duration - progress) <= 10000
    track_hash = sha256(track_title.encode()).hexdigest()
    track = db_session.query(Track).filter_by(hash=track_hash).first()
    if state["is_playing"]:
        if track and ten_seconds_left:
            await update_listened_count(track, db_session, access_token)
        elif not track and ten_seconds_passed:
            await create_track_entry(track_title, track_hash, db_session)


async def create_track_entry(
    track_title: str, track_hash: str, db_session: Session
) -> None:
    """
    Create a new track entry in the database.

    Args:
        track_title (str): The title of the track.
        track_hash (str): The hash of the track title.
        db_session (Session): SQLAlchemy database session.
    """
    track = Track(title=track_title, hash=track_hash, listened_count=0)
    db_session.add(track)
    db_session.commit()


async def update_listened_count(
    track: Track, db_session: Session, access_token: str
) -> None:
    """
    Update the listened count for a track in the database.

    Args:
        track (Track): The track instance.
        db_session (Session): SQLAlchemy database session.
        access_token (str): Spotify user access token.
    """
    track.listened_count += 1
    db_session.commit()
    await wait_for_song_change(access_token, track.title)


async def wait_for_song_change(access_token: str, current_track_title: str) -> None:
    """
    Wait until the currently playing song changes.

    Args:
        access_token (str): Spotify user access token.
        current_track_title (str): The current track title.
    """
    while True:
        state = await playback_state(access_token)
        new_track_title = state["item"]["name"]
        if new_track_title != current_track_title:
            break
        await asyncio.sleep(1)


@router.post("/poll-tracks")
async def poll_tracks(
    background_tasks: BackgroundTasks, access_token: str, db: Session = Depends(get_db)
) -> dict:
    """
    Start a background task to poll the playback state.

    Args:
        background_tasks (BackgroundTasks): FastAPI's background task manager.
        access_token (str): Spotify user access token.
        db (Session): SQLAlchemy database session.

    Returns:
        dict: Confirmation message.
    """
    background_tasks.add_task(poll_playback_state, access_token, db)
    return {"message": "Playback state polling started in the background."}


@router.get("/recently-played-tracks")
async def get_recently_played(access_token: str, limit: int = 1) -> dict:
    """
    Fetch the recently played tracks from the user's Spotify account.

    Args:
        access_token (str): Spotify user access token.
        limit (int, optional): Number of recently played tracks to fetch. Defaults to 1.

    Returns:
        dict: JSON response with the recently played tracks.

    Raises:
        HTTPException: If the Spotify API response is unsuccessful.
    """
    url = f"https://api.spotify.com/v1/me/player/recently-played?limit={limit}"
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail=response.text)
