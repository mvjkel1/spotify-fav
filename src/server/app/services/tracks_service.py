import asyncio

import httpx
from app.db.models import Track, UserPollingStatus
from app.services.token_manager import get_spotify_headers
from app.services.user_auth_service import get_current_user_id, is_user_authorized
from app.services.utils import config
from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session


async def get_current_track(db_session: Session) -> dict:
    """
    Retrieve the current track the user is listening to on Spotify.

    Args:
        db_session (Session): The SQLAlchemy session to interact with the database.

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
        db_session (Session): The SQLAlchemy session to interact with the database.
    """
    user_id = await get_current_user_id(db_session)
    continue_polling = True
    while continue_polling:
        state = await get_playback_state(db_session)
        await handle_playing_track(state, db_session)
        current_user_polling_status = await get_user_polling_status(user_id, db_session)
        continue_polling = current_user_polling_status.is_polling
        await asyncio.sleep(1)


async def get_recently_played_tracks(db_session: Session, limit: int = 1) -> dict:
    """
    Retrieve the user's recently played tracks from Spotify.

    Args:
        db_session (Session): The SQLAlchemy session to interact with the database.
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
        db_session (Session): The SQLAlchemy session to interact with the database.

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
        db_session (Session): The SQLAlchemy session to interact with the database.
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
        db_session (Session): The SQLAlchemy session to interact with the database.
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
        db_session (Session): The SQLAlchemy session to interact with the database.
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
        db_session (Session): The SQLAlchemy session to interact with the database.
    """
    track = Track(title=track_title, spotify_id=track_id, listened_count=0)
    db_session.add(track)
    db_session.commit()


async def update_track_listened_count(track: Track, db_session: Session) -> None:
    """
    Update the listened count for an existing track in the database.

    Args:
        track (Track): The track object to update.
        db_session (Session): The SQLAlchemy session to interact with the database.
    """
    track.listened_count += 1
    db_session.commit()
    await wait_for_song_change(track.title, db_session)


async def wait_for_song_change(current_track_title: str, db_session: Session) -> None:
    """
    Continuously check if the current song has changed, and wait until it does.

    Args:
        current_track_title (str): The title of the currently playing track.
        db_session (Session): The SQLAlchemy session to interact with the database.
    """
    while True:
        state = await get_playback_state(db_session)
        new_track_title = state["item"]["name"]
        if new_track_title != current_track_title:
            break
        await asyncio.sleep(1)


async def update_polling_status(
    db_session: Session, enable: bool = True, user_id: int = None
) -> None:
    """
    Update the polling status for a specific user or all users.

    If a `user_id` is provided, the function updates or creates the polling status for that user.
    If no `user_id` is provided, the function updates the polling status for all users.

    Args:
        db_session (Session): The SQLAlchemy session to interact with the database.
        enable (bool): Whether to enable or disable polling. Default is True.
        user_id (int, optional): The ID of the user to update. If None, updates all users.
    """
    if user_id:
        user_polling_status = db_session.query(UserPollingStatus).filter_by(user_id=user_id).first()

        if not user_polling_status:
            user_polling_status = UserPollingStatus(user_id=user_id)
            db_session.add(user_polling_status)

        user_polling_status.is_polling = enable
    else:
        db_session.query(UserPollingStatus).update({"is_polling": enable})
    db_session.commit()


async def get_user_polling_status(user_id: int, db_session: Session) -> UserPollingStatus:
    """
    Retrieve the polling status for the currently logged-in user.

    Args:
        user_id (int): The user ID to get the polling status of.
        db_session (Session): The SQLAlchemy session to interact with the database.

    Returns:
        UserPollingStatus: The polling status record for the user, or None if it does not exist.
    """
    return db_session.query(UserPollingStatus).filter_by(user_id=user_id).first()


def fetch_listened_tracks(db_session: Session) -> list[Track]:
    """
    Fetch tracks from the database that have been listened to (i.e., have a nonzero listened count).

    Args:
        db_session (Session): The SQLAlchemy session to interact with the database.

    Raises:
        HTTPException: Listened tracks were not found.

    Returns:
        list[Track]: A list of tracks with a listened count greater than zero.
    """
    tracks_db = db_session.query(Track).filter(Track.listened_count > 0).all()
    if not tracks_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tracks you have listened to were found.",
        )
    return tracks_db


async def start_polling_tracks(
    background_tasks: BackgroundTasks, db_session: Session
) -> dict[str, str]:
    """
     Handle the logic for starting polling of tracks in the background.

     Args:
         background_tasks (BackgroundTasks): The background task manager.
         db_session (Session): The SQLAlchemy session to interact with the database.

    Returns:
         dict[str, str]: A message indicating that polling has started.

     Raises:
         HTTPException: User is not authorized or polling is already active.
    """
    user_id = await get_current_user_id(db_session)
    current_user_polling_status = await get_user_polling_status(user_id, db_session)
    if current_user_polling_status.is_polling:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "The polling session for current user has been already started.",
        )
    if is_user_authorized(db_session):
        await update_polling_status(db_session, enable=True, user_id=user_id)
        background_tasks.add_task(poll_playback_state, db_session)
        return {"message": "Playback state polling started in the background."}
    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED, "Unauthorized - to start the polling you have to login first."
    )


async def stop_polling_tracks(db_session: Session) -> dict[str, str]:
    """
    Handle the logic for stopping the tracks polling process.

    Args:
        background_tasks (BackgroundTasks): The background task manager.
        db_session (Session): The SQLAlchemy session to interact with the database.

    Returns:
        dict[str, str]: A message indicating that polling has been stopped.

    Raises:
        HTTPException: User is not authorized or polling is not active.
    """
    user_id = await get_current_user_id(db_session)
    current_user_polling_status = await get_user_polling_status(user_id, db_session)
    if not current_user_polling_status.is_polling:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "The polling session for current user was not started.",
        )
    if is_user_authorized(db_session):
        await update_polling_status(db_session, enable=False, user_id=user_id)
        return {"message": "Polling session has been stopped successfully"}
    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Unauthorized - to stop polling you have to login first.",
    )
