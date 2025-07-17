from contextlib import asynccontextmanager

import app.routers.playlists_router as playlists_router
import app.routers.spotify_auth_router as spotify_auth_router
import app.routers.tracks_router as tracks_router
import app.routers.user_auth_router as user_auth_router
from app.db.database import async_get_db
from app.services.tracks_service import update_polling_status
from fastapi import FastAPI, Request
from prometheus_client import Histogram, make_wsgi_app
from starlette.middleware.wsgi import WSGIMiddleware

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds", "Duration of HTTP requests in seconds", ["method", "endpoint"]
)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    db_session = await anext(async_get_db())
    try:
        yield
    finally:
        await update_polling_status(db_session, enable=False)


app = FastAPI(lifespan=app_lifespan)


@app.middleware("http")
async def track_request_duration(request: Request, call_next):
    method = request.method
    endpoint = request.url.path

    with REQUEST_DURATION.labels(method=method, endpoint=endpoint).time():
        response = await call_next(request)
    return response


app.include_router(user_auth_router.router)
app.include_router(tracks_router.router)
app.include_router(playlists_router.router)
app.include_router(spotify_auth_router.router)
app.mount("/metrics", WSGIMiddleware(make_wsgi_app()))
