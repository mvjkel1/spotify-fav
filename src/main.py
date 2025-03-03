from fastapi import FastAPI

from . import endpoints

app = FastAPI()

app.include_router(endpoints.user_auth.router, prefix="/user-auth")
app.include_router(endpoints.user_auth.router, prefix="/music")
app.include_router(endpoints.user_auth.router, prefix="/client-auth")
