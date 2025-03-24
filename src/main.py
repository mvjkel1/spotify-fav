from fastapi import FastAPI

from endpoints import auth, music

app = FastAPI()

app.include_router(auth.router, prefix="/auth")
app.include_router(music.router, prefix="/music")
