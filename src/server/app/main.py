import app.endpoints.playlists as playlists
import app.endpoints.tracks as tracks
import app.endpoints.user_auth as user_auth
import app.endpoints.test as test
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_auth.router, prefix="/user-auth")
app.include_router(tracks.router, prefix="/music")
app.include_router(playlists.router, prefix="/music")
app.include_router(test.router, prefix="/test")
