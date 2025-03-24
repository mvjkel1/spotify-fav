from app.db.database import get_db
from app.services.tracks_service import (
    get_current_track,
    get_current_user_id,
    get_playback_state,
    get_recently_played_tracks,
    get_user_polling_status,
    start_polling_tracks,
    stop_polling_tracks,
    update_polling_status,
)
from app.services.user_auth_service import is_user_authorized
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

router = APIRouter(tags=["tracks"], prefix="/tracks")


@router.get("/current-track")
async def current_track(db_session: Session = Depends(get_db)) -> dict:
    """
    Retrieve the current track being played.

    Args:
        db_session (Session): The SQLAlchemy session to interact with the database.

    Returns:
        dict: A dictionary containing details of the current track.
    """
    return await get_current_track(db_session)


@router.post("/poll")
async def poll(
    background_tasks: BackgroundTasks, db_session: Session = Depends(get_db)
) -> dict[str, str]:
    """
    Start polling the playback state in the background.

    Args:
        background_tasks (BackgroundTasks): The background task manager.
        db_session (Session): The SQLAlchemy session to interact with the database.

    Raises:
        HTTPException: User is not authorized to start the polling process (missing token).

    Returns:
        dict[str, str]: A message indicating that polling has started.
    """
    return await start_polling_tracks(background_tasks, db_session)


@router.post("/stop-polling")
async def stop_polling(db_session: Session = Depends(get_db)) -> dict[str, str]:
    """
    Stop the playback state polling.

    Args:
        db_session (Session): The SQLAlchemy session to interact with the database.

    Returns:
        dict[str, str]: A message indicating that polling has been stopped.
    """
    return await stop_polling_tracks(db_session)


@router.get("/recently-played")
async def get_recently_played(limit: int = 1, db_session: Session = Depends(get_db)) -> dict:
    """
    Retrieve recently played tracks.

    Args:
        limit (int): The number of recently played tracks to retrieve. Default is 1.
        db_session (Session): The SQLAlchemy session to interact with the database.

    Returns:
        dict: A dictionary containing details of the recently played tracks.
    """
    return await get_recently_played_tracks(db_session, limit)


@router.get("/playback-state")
async def playback_state(db_session: Session = Depends(get_db)) -> dict:
    """
    Retrieve the current playback state.

    Args:
        db_session (Session): The SQLAlchemy session to interact with the database.

    Returns:
        dict: A dictionary containing details of the current playback state.
    """
    return await get_playback_state(db_session)
