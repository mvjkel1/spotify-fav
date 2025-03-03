from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from endpoints import playlists, tracks, user_auth

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
