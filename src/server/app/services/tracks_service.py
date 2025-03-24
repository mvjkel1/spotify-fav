import asyncio

import httpx
from app.db.models import Track
from app.utils import config, get_spotify_headers
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


async def get_current_track(db_session: Session) -> dict:
    url = f"{config['SPOTIFY_API_URL']}/me/player/currently-playing"
    headers = await get_spotify_headers(db_session)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == status.HTTP_200_OK:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail=response.text)


async def poll_playback_state(db_session: Session) -> None:
    state = await get_playback_state(db_session)
    await handle_playing_track(state, db_session)
    while True:
        try:
            state = await get_playback_state(db_session)
            await handle_playing_track(state, db_session)
        except HTTPException as exc:
            print(f"Error fetching playback state: {exc}")
        except SQLAlchemyError as exc:
            print(f"Database error: {exc}")
        except Exception as exc:
            print(f"Unexpected error: {exc}")
        await asyncio.sleep(1)


async def get_recently_played_track(db_session: Session, limit: int = 1) -> dict:
    url = f"{config['SPOTIFY_API_URL']}/me/player/recently-played?limit={limit}"
    headers = await get_spotify_headers(db_session)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == status.HTTP_200_OK:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail=response.text)


async def get_playback_state(db_session: Session) -> dict:
    url = f"{config['SPOTIFY_API_URL']}/me/player"
    headers = await get_spotify_headers(db_session)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == status.HTTP_200_OK:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail=response.text)


async def handle_playing_track(state: dict, db_session: Session) -> dict:
    progress, duration = state["progress_ms"], state["item"]["duration_ms"]
    ten_seconds_passed, ten_seconds_left = (
        progress >= 10000,
        (duration - progress) <= 10000,
    )
    track_title, track_id = state["item"]["name"], state["item"]["id"]
    track_query = db_session.query(Track).filter_by(title=track_title)
    track_db = track_query.first()
    if state["is_playing"]:
        if track_db and ten_seconds_left:
            await update_track_listened_count(track_db, db_session)
        elif not track_db and ten_seconds_passed:
            await create_track_entry(track_title, track_id, db_session)


async def create_track_entry(track_title: str, track_id: int, db_session: Session) -> None:
    track = Track(title=track_title, spotify_id=track_id, listened_count=0)
    db_session.add(track)
    db_session.commit()


async def update_track_listened_count(track: Track, db_session: Session) -> None:
    track.listened_count += 1
    db_session.commit()
    await wait_for_song_change(db_session, track.title)


async def wait_for_song_change(db_session: Session, current_track_title: str) -> None:
    while True:
        state = await get_playback_state(db_session)
        new_track_title = state["item"]["name"]
        print(new_track_title, current_track_title)
        if new_track_title != current_track_title:
            break
        await asyncio.sleep(1)
