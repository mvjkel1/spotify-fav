import asyncio

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import Track
from app.token_manager import get_spotify_headers
from app.utils import config


async def get_current_track(db_session: Session) -> dict:
    """
    Retrieve the current track the user is listening to on Spotify.

    Args:
        db_session (Session): SQLAlchemy session to get Spotify headers.

    Returns:
        dict: A dictionary containing information about the current track.

    Raises:
        HTTPException: If the request to Spotify fails or returns a non-200 status code.
    """
    url = f"{config['SPOTIFY_API_URL']}/me/player/currently-playing"
    headers = await get_spotify_headers(db_session)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=f"Failed to fetch current track: {exc.response.text}",
            ) from exc
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error connecting to Spotify API: {str(exc)}",
            ) from exc
        return response.json()


async def poll_playback_state(db_session: Session) -> None:
    """
    Poll the playback state periodically in the background and handle the current playing track.

    Args:
        db_session (Session): The database session to use for querying or updating the database.
    """
    while True:
        state = await get_playback_state(db_session)
        await handle_playing_track(state, db_session)
        await asyncio.sleep(1)


async def get_recently_played_tracks(db_session: Session, limit: int = 1) -> dict:
    """
    Retrieve the user's recently played tracks from Spotify.

    Args:
        db_session (Session): SQLAlchemy session to get Spotify headers.
        limit (int, optional): The number of recent tracks to retrieve. Defaults to 1.

    Returns:
        dict: A dictionary containing information about the recently played track(s).

    Raises:
        HTTPException: If the request to Spotify fails or returns a non-200 status code.
    """
    url = f"{config['SPOTIFY_API_URL']}/me/player/recently-played?limit={limit}"
    headers = await get_spotify_headers(db_session)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=f"Failed to fetch recently played tracks: {exc.response.text}",
            ) from exc
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error connecting to Spotify API: {str(exc)}",
            ) from exc
        return response.json()


async def get_playback_state(db_session: Session) -> dict:
    """
    Retrieve the user's current playback state from Spotify.

    Args:
        db_session (Session): SQLAlchemy session to get Spotify headers.

    Returns:
        dict: A dictionary containing the current playback state information.

    Raises:
        HTTPException: If the request to Spotify fails or returns a non-200 status code.
    """
    url = f"{config['SPOTIFY_API_URL']}/me/player"
    headers = await get_spotify_headers(db_session)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=f"Failed to fetch playback state: {exc.response.text}",
            ) from exc
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error connecting to Spotify API: {str(exc)}",
            ) from exc
        return response.json()


async def handle_playing_track(state: dict, db_session: Session) -> None:
    """
    Handle the logic for the currently playing track, updating the database as necessary.

    Args:
        state (dict): The current playback state returned from Spotify.
        db_session (Session): The database session to use for querying or updating the database.
    """
    progress, duration, track_title, track_id = extract_track_data(state)
    ten_seconds_passed, ten_seconds_left = check_track_progress(progress, duration)
    track_db = get_track_from_db(db_session, track_title)
    if state.get("is_playing"):
        await process_playing_track(
            track_db, ten_seconds_passed, ten_seconds_left, track_title, track_id, db_session
        )


def extract_track_data(state: dict) -> tuple[str, str, str, str]:
    """
    Extract the necessary track data from the playback state.

    Args:
        state (dict): The current playback state returned from Spotify.

    Returns:
        tuple[str, str, str, str]: A tuple containing the track's progress, duration, title, and Spotify ID.

    Raises:
        HTTPException: If any required data is missing.
    """
    try:
        progress = state["progress_ms"]
        item = state["item"]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing data in playback state.",
        )
    return progress, item["duration_ms"], item["name"], item["id"]


def check_track_progress(progress: int, duration: int) -> tuple[bool, bool]:
    """
    Check if certain time thresholds in the track's progress are met.

    Args:
        progress (int): The current progress of the track in milliseconds.
        duration (int): The total duration of the track in milliseconds.

    Returns:
        tuple[bool, bool]: A tuple containing two boolean values:
                            - True if 10 seconds or more have passed,
                            - True if 10 seconds or less remain in the track.
    """
    ten_seconds_passed = progress >= 10000
    ten_seconds_left = (duration - progress) <= 10000
    return ten_seconds_passed, ten_seconds_left


def get_track_from_db(db_session: Session, track_title: str) -> Track | None:
    """
    Query the database for a track by its title.

    Args:
        db_session (Session): The database session to use for querying the Track model.
        track_title (str): The title of the track to search for.

    Returns:
        Track | None: The Track object if found, otherwise None.
    """
    track_query = db_session.query(Track).filter_by(title=track_title)
    return track_query.first()


async def process_playing_track(
    track_db: Track | None,
    ten_seconds_passed: bool,
    ten_seconds_left: bool,
    track_title: str,
    track_id: str,
    db_session: Session,
) -> None:
    """
    Process the currently playing track by updating its listen count or creating a new entry in the database.

    Args:
        track_db (Track | None): The track from the database if it exists, or None if not found.
        ten_seconds_passed (bool): True if 10 seconds or more have passed in the track.
        ten_seconds_left (bool): True if 10 seconds or less remain in the track.
        track_title (str): The title of the currently playing track.
        track_id (str): The Spotify ID of the currently playing track.
        db_session (Session): The database session to use for updates.
    """
    if track_db and ten_seconds_left:
        await update_track_listened_count(track_db, db_session)
    elif not track_db and ten_seconds_passed:
        await create_track_entry(track_title, track_id, db_session)


async def create_track_entry(track_title: str, track_id: str, db_session: Session) -> None:
    """
    Create a new track entry in the database if the track is not found.

    Args:
        track_title (str): The title of the track.
        track_id (str): The Spotify ID of the track.
        db_session (Session): The database session to use for adding the track.
    """
    track = Track(title=track_title, spotify_id=track_id, listened_count=0)
    db_session.add(track)
    db_session.commit()


async def update_track_listened_count(track: Track, db_session: Session) -> None:
    """
    Update the listened count for an existing track in the database.

    Args:
        track (Track): The track object to update.
        db_session (Session): The database session to use for committing changes.
    """
    track.listened_count += 1
    db_session.commit()
    await wait_for_song_change(db_session, track.title)


async def wait_for_song_change(db_session: Session, current_track_title: str) -> None:
    """
    Continuously check if the current song has changed, and wait until it does.

    Args:
        db_session (Session): The database session to use for retrieving playback state.
        current_track_title (str): The title of the currently playing track.
    """
    while True:
        state = await get_playback_state(db_session)
        new_track_title = state["item"]["name"]
        if new_track_title != current_track_title:
            break
        await asyncio.sleep(1)
