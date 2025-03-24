from app.db.database import get_db
from app.services.tracks_service import (
    get_current_track,
    get_playback_state,
    get_recently_played_track,
    poll_playback_state,
)
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

router = APIRouter(tags=["tracks"], prefix="/tracks")


@router.get("/current-track")
async def current_track(db_session: Session = Depends(get_db)) -> dict:
    return await get_current_track(db_session)


@router.post("/poll")
async def poll(
    background_tasks: BackgroundTasks, db_session: Session = Depends(get_db)
) -> dict:
    background_tasks.add_task(poll_playback_state, db_session)
    return {"message": "Playback state polling started in the background."}


@router.get("/recently-played")
async def get_recently_played(
    db_session: Session = Depends(get_db), limit: int = 1
) -> dict:
    return await get_recently_played_track(db_session, limit)


@router.get("/playback-state")
async def playback_state(db_session: Session = Depends(get_db)) -> dict:
    return await get_playback_state(db_session)
