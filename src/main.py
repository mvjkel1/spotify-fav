from fastapi import FastAPI

from endpoints import client_auth, music, user_auth

app = FastAPI()

app.include_router(user_auth.router, prefix="/user-auth")
app.include_router(music.router, prefix="/music")
app.include_router(client_auth.router, prefix="/client-auth")
