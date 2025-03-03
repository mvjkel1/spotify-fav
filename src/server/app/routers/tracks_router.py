from app.db.database import get_db
from app.services.tracks_service import (
    get_current_track,
    get_playback_state,
    get_recently_played_tracks,
    poll_playback_state,
)
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.services.user_auth_service import is_user_authorized

router = APIRouter(tags=["tracks"], prefix="/tracks")


@router.get("/current-track")
async def current_track(db_session: Session = Depends(get_db)) -> dict[str, str]:
    """
    Retrieve the current track being played.

    Args:
        db_session (Session): The database session to use.

    Returns:
        dict[str, str]: A dictionary containing details of the current track.
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
        db_session (Session): The database session to use.

    Returns:
        dict[str, str]: A message indicating that polling has started.
    """
    # Workaround to don't add background tasks if there was an exception within poll_playback_state func call,
    # it should be improved in the future
    if is_user_authorized(db_session):
        background_tasks.add_task(poll_playback_state, db_session)
        return {"message": "Playback state polling started in the background."}
    raise HTTPException(404, "Unauthorized - to start the polling you have to login first.")


@router.get("/recently-played")
async def get_recently_played(
    limit: int = 1, db_session: Session = Depends(get_db)
) -> dict[str, str]:
    """
    Retrieve recently played tracks.

    Args:
        db_session (Session): The database session to use.
        limit (int): The number of recently played tracks to retrieve. Default is 1.

    Returns:
        dict[str, str]: A dictionary containing details of the recently played tracks.
    """
    return await get_recently_played_tracks(db_session, limit)


@router.get("/playback-state")
async def playback_state(db_session: Session = Depends(get_db)) -> dict[str, str]:
    """
    Retrieve the current playback state.

    Args:
        db_session (Session): The database session to use.

    Returns:
        dict[str, str]: A dictionary containing details of the current playback state.
    """
    return await get_playback_state(db_session)
