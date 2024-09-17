import asyncio

import httpx
from app.db.database import get_db
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from app.db.models import Track
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.token_manager import get_token
from app.utils import config, get_spotify_headers

router = APIRouter(tags=["music"])


@router.get("/current_music")
async def current_track(db_session: Session = Depends(get_db)) -> dict:
    """
    Fetch the currently playing track from the user's Spotify account.

    Args:
        db_session (Session): The database session dependency used to obtain headers.

    Returns:
        dict: A JSON response containing details about the currently playing track.

    Raises:
        HTTPException: If the Spotify API response is unsuccessful, an HTTPException is raised
        with the status code and error details from the response.
    """
    url = f"{config['SPOTIFY_API_URL']}/me/player/currently-playing"
    headers = await get_spotify_headers(db_session)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail=response.text)


@router.get("/playback_state")
async def playback_state(db_session: Session = Depends(get_db)) -> dict:
    """
    Fetch the current playback state from the user's Spotify account.

    Args:
        db_session (Session): The database session dependency used to obtain headers.

    Returns:
        dict: A JSON response containing the current playback state.

    Raises:
        HTTPException: If the Spotify API response is unsuccessful, an HTTPException is raised
        with the status code and error details from the response.
    """
    url = f"{config['SPOTIFY_API_URL']}/me/player"
    headers = await get_spotify_headers(db_session)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail=response.text)


async def poll_playback_state(access_token: str, db_session: Session) -> None:
    """
    Continuously poll the playback state and update the database with the current track information.

    Args:
        access_token (str): The Spotify access token.
        db_session (Session): SQLAlchemy database session used for database operations.
    """
    while True:
        try:
            state = await playback_state(db_session)
            await handle_playing_track(state, db_session, access_token)
        except HTTPException as exc:
            print(f"Error fetching playback state: {exc}")
        except SQLAlchemyError as exc:
            print(f"Database error: {exc}")
        except Exception as exc:
            print(f"Unexpected error: {exc}")
        await asyncio.sleep(1)


async def handle_playing_track(state: dict, db_session: Session, access_token: str) -> None:
    """
    Handle the logic for a track that is currently playing.

    Args:
        state (dict): The current playback state from Spotify.
        db_session (Session): SQLAlchemy database session used for database operations.
        access_token (str): The Spotify access token.
    """
    progress, duration = state["progress_ms"], state["item"]["duration_ms"]
    ten_seconds_passed, ten_seconds_left = (
        progress >= 10000,
        (duration - progress) <= 10000,
    )
    track_title, track_id = state["item"]["name"], state["item"]["id"]
    track_query = db_session.query(Track).filter_by(title=track_title)
    track_db = track_query.first()
    if state["is_playing"]:
        if track_db and ten_seconds_left:
            await update_track_listened_count(track_db, db_session, access_token)
        elif not track_db and ten_seconds_passed:
            await create_track_entry(track_title, track_id, db_session)


async def create_track_entry(track_title: str, track_id: int, db_session: Session) -> None:
    """
    Create a new track entry in the database.

    Args:
        track_title (str): The title of the track.
        track_id (int): The Spotify ID of the track.
        db_session (Session): SQLAlchemy database session used for database operations.
    """
    track = Track(title=track_title, spotify_id=track_id, listened_count=0)
    db_session.add(track)
    db_session.commit()


async def update_track_listened_count(track: Track, db_session: Session, access_token: str) -> None:
    """
    Update the listened count for a track in the database.

    Args:
        track (Track): The track instance to update.
        db_session (Session): SQLAlchemy database session used for database operations.
        access_token (str): The Spotify access token.
    """
    track.listened_count += 1
    db_session.commit()
    db_session.close()
    await wait_for_song_change(access_token, track.title)


async def wait_for_song_change(access_token: str, current_track_title: str) -> None:
    """
    Wait until the currently playing song changes.

    Args:
        access_token (str): The Spotify access token.
        current_track_title (str): The title of the currently playing track.
    """
    while True:
        state = await playback_state(access_token)
        new_track_title = state["item"]["name"]
        if new_track_title != current_track_title:
            break
        await asyncio.sleep(1)


@router.post("/poll-tracks")
async def poll_tracks(
    background_tasks: BackgroundTasks, db_session: Session = Depends(get_db)
) -> dict:
    """
    Start a background task to poll the playback state.

    Args:
        background_tasks (BackgroundTasks): FastAPI's background task manager.
        db_session (Session): SQLAlchemy database session used for database operations.

    Returns:
        dict: A confirmation message indicating that the background task has started.
    """
    token = get_token(db_session)
    background_tasks.add_task(poll_playback_state, token["access_token"], db_session)
    return {"message": "Playback state polling started in the background."}


@router.get("/recently-played-tracks")
async def get_recently_played(db_session: Session = Depends(get_db), limit: int = 1) -> dict:
    """
    Fetch the recently played tracks from the user's Spotify account.

    Args:
        db_session (Session): The database session dependency used to obtain headers.
        limit (int): Number of recently played tracks to fetch. Default is 1.

    Returns:
        dict: A JSON response containing the recently played tracks.

    Raises:
        HTTPException: If the Spotify API response is unsuccessful, an HTTPException is raised
        with the status code and error details from the response.
    """
    url = f"{config['SPOTIFY_API_URL']}/me/player/recently-played?limit={limit}"
    headers = await get_spotify_headers(db_session)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail=response.text)
