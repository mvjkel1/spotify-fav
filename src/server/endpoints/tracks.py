import asyncio

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import get_db
from models import Track
from token_manager import token_manager
from utils import get_spotify_headers, config, refresh_token

router = APIRouter(tags=["music"])


@router.get("/current_music")
async def current_track() -> dict:
    """
    Fetch the currently playing track from the user's Spotify account.

    Args:
        access_token (str): Spotify user access token.

    Returns:
        dict: JSON response with the currently playing track.

    Raises:
        HTTPException: If the Spotify API response is unsuccessful.
    """
    url = f"{config['SPOTIFY_API_URL']}/me/player/currently-playing"
    headers = get_spotify_headers()
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail=response.text)


@router.get("/playback_state")
async def playback_state() -> dict:
    """
    Fetch the current playback state from the user's Spotify account.

    Returns:
        dict: JSON response with the playback state.

    Raises:
        HTTPException: If the Spotify API response is unsuccessful.
    """
    url = f"{config['SPOTIFY_API_URL']}/me/player"
    headers = get_spotify_headers()
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail=response.text)


@refresh_token
async def poll_playback_state(db_session: Session = Depends(get_db)) -> None:
    """
    Continuously poll the playback state and update the database with the current track information.

    Args:
        db_session (Session): SQLAlchemy database session.
    """
    while True:
        try:
            access_token, _ = token_manager.get_tokens()
            state = await playback_state(access_token)
            await handle_playing_track(state, db_session, access_token)
        except HTTPException as exc:
            print(f"Error fetching playback state: {exc}")
        except SQLAlchemyError as exc:
            print(f"Database error: {exc}")
        except Exception as exc:
            print(f"Unexpected error: {exc}")
        await asyncio.sleep(1)


@refresh_token
async def handle_playing_track(state: dict, db_session: Session = Depends(get_db)) -> None:
    """
    Handle the logic for a track that is currently playing.

    Args:
        state (dict): Current playback state.
        db_session (Session): SQLAlchemy database session.
    """
    access_token, _ = token_manager.get_tokens()
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


async def create_track_entry(
    track_title: str, track_id: int, db_session: Session = Depends(get_db)
) -> None:
    """
    Create a new track entry in the database.

    Args:
        track_title (str): The title of the track.
        track_id (int): The spotify_id of the track.
        db_session (Session): SQLAlchemy database session.
    """
    try:
        track = Track(title=track_title, spotify_id=track_id, listened_count=0)
        db_session.add(track)
        db_session.commit()
    except SQLAlchemyError:
        db_session.rollback()
    finally:
        db_session.close()


@refresh_token
async def update_track_listened_count(track: Track, db_session: Session = Depends(get_db)) -> None:
    """
    Update the listened count for a track in the database.

    Args:
        track (Track): The track instance.
        db_session (Session): SQLAlchemy database session.
    """
    access_token, _ = token_manager.get_tokens()
    track.listened_count += 1
    db_session.commit()
    db_session.close()
    await wait_for_song_change(access_token, track.title)


@refresh_token
async def wait_for_song_change(current_track_title: str) -> None:
    """
    Wait until the currently playing song changes.

    Args:
        current_track_title (str): The current track title.
    """
    access_token, _ = token_manager.get_tokens()
    while True:
        state = await playback_state(access_token)
        new_track_title = state["item"]["name"]
        if new_track_title != current_track_title:
            break
        await asyncio.sleep(1)


@refresh_token
@router.post("/poll-tracks")
async def poll_tracks(
    background_tasks: BackgroundTasks, db_session: Session = Depends(get_db)
) -> dict:
    """
    Start a background task to poll the playback state.

    Args:
        background_tasks (BackgroundTasks): FastAPI's background task manager.
        db_session (Session): SQLAlchemy database session.

    Returns:
        dict: Confirmation message.
    """
    access_token, _ = token_manager.get_tokens()
    background_tasks.add_task(poll_playback_state, access_token, db_session)
    return {"message": "Playback state polling started in the background."}


@router.get("/recently-played-tracks")
async def get_recently_played(limit: int = 1) -> dict:
    """
    Fetch the recently played tracks from the user's Spotify account.

    Args:
        limit (int): Number of recently played tracks to fetch. Default is 1.

    Returns:
        dict: JSON response with the recently played tracks.

    Raises:
        HTTPException: If the Spotify API response is unsuccessful.
    """
    url = f"{config['SPOTIFY_API_URL']}/me/player/recently-played?limit={limit}"
    headers = get_spotify_headers()
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail=response.text)
