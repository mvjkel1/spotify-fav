from fastapi import FastAPI

import app.routers.playlists_router as playlists_router
import app.routers.tracks_router as tracks_router
import app.routers.user_auth_router as user_auth_router

app = FastAPI()

app.include_router(user_auth_router.router)
app.include_router(tracks_router.router)
app.include_router(playlists_router.router)
