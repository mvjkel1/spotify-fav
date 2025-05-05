from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, status
from sqlalchemy.ext.asyncio.session import AsyncSession

from app.db.database import async_get_db
from app.db.schemas import UserSchema
from app.services.tracks_service import (
    fetch_listened_tracks,
    get_current_track,
    get_playback_state,
    get_recently_played_tracks,
    start_polling_tracks,
    stop_polling_tracks,
)
from app.services.user_auth_service import get_current_active_user

router = APIRouter(tags=["tracks"], prefix="/tracks")


@router.get("/current")
async def current_track(
    current_user: Annotated[UserSchema, Depends(get_current_active_user)],
    db_session: AsyncSession = Depends(async_get_db),
) -> dict:
    """
    Retrieve the current track being played.

    Args:
        current_user (UserSchema): The currently authenticated user, provided by the dependency get_current_active_user.
        db_session (AsyncSession): The SQLAlchemy session used to query the database for the user's current track.
    Returns:
        dict: A dictionary containing details of the current track.
    """
    return await get_current_track(current_user.id, db_session)


@router.post("/polling/start")
async def start_polling(
    background_tasks: BackgroundTasks,
    current_user: Annotated[UserSchema, Depends(get_current_active_user)],
    db_session: AsyncSession = Depends(async_get_db),
) -> dict[str, str]:
    """
    Start polling the playback state in the background.

    Args:
        background_tasks (BackgroundTasks): The background task manager used to schedule the polling task.
        current_user (UserSchema): The currently authenticated user, provided by the dependency get_current_active_user.
        db_session (AsyncSession): The SQLAlchemy session used to interact with the database.

    Raises:
        HTTPException: User is not authorized to start the polling process (missing token).

    Returns:
        dict[str, str]: A message indicating that polling has started.
    """
    return await start_polling_tracks(background_tasks, current_user.id, db_session)


@router.post("/polling/stop")
async def stop_polling(
    current_user: Annotated[UserSchema, Depends(get_current_active_user)],
    db_session: AsyncSession = Depends(async_get_db),
) -> dict[str, str]:
    """
    Stop the playback state polling.

    Args:
        current_user (UserSchema): The currently authenticated user, provided by the dependency get_current_active_user.
        db_session (AsyncSession): The SQLAlchemy session used to interact with the database.

    Returns:
        dict[str, str]: A message indicating that polling has been stopped.
    """
    return await stop_polling_tracks(current_user.id, db_session)


@router.get("/recently-played")
async def get_recently_played(
    current_user: Annotated[UserSchema, Depends(get_current_active_user)],
    limit: int = Query(1, ge=1, le=50),
    db_session: AsyncSession = Depends(async_get_db),
) -> dict:
    """
    Retrieve recently played tracks.

    Args:
        current_user (UserSchema): The currently authenticated user, provided by the dependency get_current_active_user.
        limit (int): The number of recently played tracks to retrieve. Default is 1.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.

    Returns:
        dict: A dictionary containing details of the recently played tracks.
    """
    return await get_recently_played_tracks(current_user.id, db_session, limit)


@router.get("/playback/state")
async def fetch_playback_state(
    current_user: Annotated[UserSchema, Depends(get_current_active_user)],
    db_session: AsyncSession = Depends(async_get_db),
) -> dict:
    """
    Retrieve the current playback state.

    Args:
        current_user (UserSchema): The currently authenticated user, provided by the dependency get_current_active_user.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.

    Returns:
        dict: A dictionary containing details of the current playback state.
    """
    playback_state = await get_playback_state(current_user.id, db_session)
    return playback_state if playback_state else Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/polled")
async def get_polled_tracks(
    current_user: Annotated[UserSchema, Depends(get_current_active_user)],
    db_session: AsyncSession = Depends(async_get_db),
):
    return await fetch_listened_tracks(current_user.id, db_session)
