from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.token_manager import refresh_access_token

router = APIRouter(tags=["test"])


@router.get("/test")
async def get_my_playlists(db_session: Session = Depends(get_db)) -> dict:
    token = await refresh_access_token(db_session)
    return {"token": token}
