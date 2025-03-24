from contextlib import asynccontextmanager

import app.routers.playlists_router as playlists_router
import app.routers.tracks_router as tracks_router
import app.routers.user_auth_router as user_auth_router
from app.db.database import get_db
from app.services.tracks_service import update_polling_status
from fastapi import FastAPI


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    db_session = next(get_db())
    yield
    await update_polling_status(db_session, enable=False)


app = FastAPI(lifespan=app_lifespan)

app.include_router(user_auth_router.router)
app.include_router(tracks_router.router)
app.include_router(playlists_router.router)
