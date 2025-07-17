import asyncio

import httpx
from app.db.models import Track, User, user_track_association_table
from app.services.spotify_token_manager import get_spotify_headers
from app.services.user_auth_service import get_current_user_db
from app.services.utils import config
from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio.session import AsyncSession


async def get_current_track(user_id: int, db_session: AsyncSession) -> dict:
    """
    Retrieve the current track the user is listening to on Spotify.

    Args:
        user_id (int): The ID of logged in user.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.

    Returns:
        dict: A dictionary containing information about the current track.

    Raises:
        HTTPException: If the request to Spotify fails or returns a non-200 status code.
    """
    url = f"{config['SPOTIFY_API_URL']}/me/player/currently-playing"
    async with httpx.AsyncClient() as client:
        try:
            spotify_headers = await get_spotify_headers(user_id, db_session)
            response = await client.get(url, headers=spotify_headers)
            response.raise_for_status()
            if response.status_code == status.HTTP_204_NO_CONTENT:
                return {"message": "No track currently playing"}
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


async def poll_playback_state(user_id: int, db_session: AsyncSession) -> None:
    """
    Poll the playback state periodically in the background and handle the current playing track.

    Args:
        user_id (int): The ID of logged in user.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.
    """
    while await is_user_polling(user_id, db_session):
        try:
            playback_state = await get_playback_state(user_id, db_session)
            if playback_state:
                await handle_playing_track(playback_state, user_id, db_session)
        except HTTPException as exc:
            await update_polling_status(False, db_session, user_id)
            break
        await asyncio.sleep(5)


async def get_recently_played_tracks(
    user_id: int, db_session: AsyncSession, limit: int = 1
) -> dict:
    """
    Retrieve the user's recently played tracks from Spotify.

    Args:
        user_id (int): The ID of logged in user.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.
        limit (int, optional): The number of recent tracks to retrieve. Defaults to 1.

    Returns:
        dict: A dictionary containing information about the recently played track(s).

    Raises:
        HTTPException: If the request to Spotify fails or returns a non-200 status code.
    """
    url = f"{config['SPOTIFY_API_URL']}/me/player/recently-played?limit={limit}"
    async with httpx.AsyncClient() as client:
        try:
            spotify_headers = await get_spotify_headers(user_id, db_session)
            response = await client.get(url, headers=spotify_headers)
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


async def get_playback_state(user_id: int, db_session: AsyncSession) -> dict:
    """
    Retrieve the user's playback state.

    Args:
        user_id (int): The ID of logged in user.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.

    Raises:
        HTTPException: If the request to Spotify fails or returns a non-200 status code.
    """
    url = f"{config['SPOTIFY_API_URL']}/me/player"
    async with httpx.AsyncClient() as client:
        try:
            spotify_headers = await get_spotify_headers(user_id, db_session)
            response = await client.get(url, headers=spotify_headers)
            response.raise_for_status()
            if response.status_code == status.HTTP_204_NO_CONTENT:
                return {}
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


async def handle_playing_track(
    playback_state: dict, user_id: str, db_session: AsyncSession
) -> None:
    """
    Handle the logic for the currently playing track, updating the database as necessary.

    Args:
        playback_state (dict): The current playback state returned from Spotify.
        user_id (int): The JWT token used to authenticate the request
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.
    """
    progress, duration, track_title, track_id = extract_track_data(playback_state)
    ten_seconds_passed, ten_seconds_left = check_track_progress(progress, duration)
    track_db = await get_track_from_db(track_title, db_session)
    if playback_state.get("is_playing"):
        await process_playing_track(
            track_db,
            ten_seconds_passed,
            ten_seconds_left,
            track_title,
            track_id,
            user_id,
            db_session,
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
        track_progress = state["progress_ms"]
        track_duration_ms = state["item"]["duration_ms"]
        track_name = state["item"]["name"]
        track_id = state["item"]["id"]
    except (KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing data in playback state.",
        ) from exc

    return track_progress, track_duration_ms, track_name, track_id


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


async def get_track_from_db(track_title: str, db_session: AsyncSession) -> Track | None:
    """
    Query the database for a track by its title.

    Args:
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.
        track_title (str): The title of the track to search for.

    Returns:
        Track | None: The Track object if found, otherwise None.
    """
    result = await db_session.execute(select(Track).filter_by(title=track_title))
    return result.scalar_one_or_none()


async def process_playing_track(
    track_db: Track | None,
    ten_seconds_passed: bool,
    ten_seconds_left: bool,
    track_title: str,
    track_id: str,
    user_id: int,
    db_session: AsyncSession,
) -> None:
    """
    Process the currently playing track by updating its listen count or creating a new entry in the database.

    Args:
        track_db (Track | None): The track from the database if it exists, or None if not found.
        ten_seconds_passed (bool): True if 10 seconds or more have passed in the track.
        ten_seconds_left (bool): True if 10 seconds or less remain in the track.
        track_title (str): The title of the currently playing track.
        track_id (str): The Spotify ID of the currently playing track.
        user_id (int): The ID of logged in user.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.
    """
    if track_db and ten_seconds_left:
        await update_track_listened_count(track_db, user_id, db_session)
    elif not track_db and ten_seconds_passed:
        await create_track_entry(track_title, track_id, user_id, db_session)


async def create_track_entry(
    track_title: str, track_id: str, user_id: int, db_session: AsyncSession
) -> None:
    """
    Create a new track entry in the database if the track is not found.

    Args:
        track_title (str): The title of the track.
        track_id (str): The Spotify ID of the track.
        user_id (int): The ID of logged in user.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.
    """
    user = await get_current_user_db(user_id, db_session)
    track = Track(title=track_title, spotify_id=track_id)
    db_session.add(track)
    await db_session.commit()
    new_entry = user_track_association_table.insert().values(
        user_id=user.id,
        track_id=track.id,
        listened_count=0,
    )
    await db_session.execute(new_entry)
    await db_session.commit()


async def update_track_listened_count(track: Track, user_id: int, db_session: AsyncSession) -> None:
    """
    Update the listened count for an existing track in the database.

    Args:
        track (Track): The track object to update.
        user_id (int): The ID of logged in user.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.
    """
    user = await get_current_user_db(user_id, db_session)
    stmt = (
        update(user_track_association_table)
        .where(
            user_track_association_table.c.user_id == user.id,
            user_track_association_table.c.track_id == track.id,
        )
        .values(
            listened_count=user_track_association_table.c.listened_count + 1,
        )
    )
    await db_session.execute(stmt)
    await db_session.commit()
    await wait_for_song_change(track.title, user_id, db_session)


async def get_listened_count(track_id: int, user_id: int, db_session: AsyncSession):
    """
    Get the number of times a track has been listened to by a specific user.

    Args:
        track_id (int): The ID of the track.
        user_id (int): The ID of the logged-in user.
        db_session (AsyncSession): The SQLAlchemy session used to interact with the database.

    Returns:
        int: The number of times the track with the given `track_id` has been listened to by the user.
    """
    result = (
        await db_session.execute(
            select(user_track_association_table.c.listened_count).where(
                user_track_association_table.c.user_id == user_id,
                user_track_association_table.c.track_id == track_id,
            )
        )
    ).scalar_one_or_none()
    return result or 0


async def wait_for_song_change(track_title: str, user_id: int, db_session: AsyncSession) -> None:
    """
    Continuously check if the current song has changed, and wait until it does.

    Args:
        track_title (str): The title of the currently playing track.
        user_id (int): The ID of logged in user.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.
    """
    while True:
        state = await get_playback_state(user_id, db_session)
        new_track_title = state["item"]["name"]
        if new_track_title != track_title:
            break
        await asyncio.sleep(1)


async def update_polling_status(
    enable: bool, db_session: AsyncSession, user_id: int | None = None
) -> None:
    """
    Enable or disable polling for a specific user or all users.

    Args:
        enable (bool): Whether to enable or disable polling.
        db_session (AsyncSession): Async SQLAlchemy session.
        user_id (int | None): If provided, only update polling for this user.
    """
    query = select(User).filter_by(id=user_id) if user_id else select(User)
    users = (await db_session.execute(query)).scalars().all()

    for user in users:
        user.is_polling = enable

    await db_session.commit()


async def is_user_polling(user_id: int, db_session: AsyncSession) -> bool:
    """
    Retrieve the polling status for the currently logged-in user.

    Args:
        user_id (int): The ID of logged in user.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.

    Returns:
        bool: True if user is polling, False otherwise.
    """
    result = await db_session.execute(select(User).filter_by(id=user_id))
    user = result.scalar_one_or_none()
    return user.is_polling if user else None


async def fetch_listened_tracks(user_id: int, db_session: AsyncSession) -> list[Track]:
    """
    Fetch tracks from the database that have been listened to (i.e., have a nonzero listened count).

    Args:
        user_id (int): The ID of logged in user.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.

    Raises:
        HTTPException: Listened tracks were not found.

    Returns:
        list[Track]: A list of tracks with a listened count greater than zero.
    """
    result = await db_session.execute(
        select(Track)
        .join(user_track_association_table, Track.id == user_track_association_table.c.track_id)
        .filter(user_track_association_table.c.user_id == user_id)
        .filter(user_track_association_table.c.listened_count > 0)
    )

    tracks = result.scalars().all()
    if not tracks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tracks you have listened to were found.",
        )
    return tracks


async def start_polling_tracks(
    background_tasks: BackgroundTasks, user_id: int, db_session: AsyncSession
) -> dict[str, str]:
    """
     Handle the logic for starting polling of tracks in the background.

     Args:
         background_tasks (BackgroundTasks): The background task manager.
         user_id (int): The ID of logged in user.
         db_session (AsyncSession): The SQLAlchemy async session used to query the database.

    Returns:
         dict[str, str]: A message indicating that polling has started.

     Raises:
         HTTPException: User is not authorized or polling is already active.
    """
    user = await get_current_user_db(user_id, db_session)
    if not user.spotify_uid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authorize your Spotify account first.")
    if user.is_polling:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "The polling session for current user has already started.",
        )
    await update_polling_status(True, db_session, user_id)
    background_tasks.add_task(poll_playback_state, user_id, db_session)
    return {"message": "Playback state polling started in the background."}


async def stop_polling_tracks(user_id: int, db_session: AsyncSession) -> dict[str, str]:
    """
    Handle the logic for stopping the tracks polling process.

    Args:
        user_id (int): The ID of logged in user.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.

    Returns:
        dict[str, str]: A message indicating that polling has been stopped.

    Raises:
        HTTPException: User is not authorized or polling is not active.
    """
    user = await get_current_user_db(user_id, db_session)
    if not user.spotify_uid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authorize your Spotify account first.")
    if not user.is_polling:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "The polling session for current user has not started.",
        )
    await update_polling_status(False, db_session, user_id)
    return {"message": "Polling session has been stopped successfully"}
