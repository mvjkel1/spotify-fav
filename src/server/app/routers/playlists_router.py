import httpx
from app.db.database import get_db
from app.services.playlists_service import (
    add_tracks_to_playlist,
    create_playlist_in_db,
    create_playlist_on_spotify,
    get_my_playlists_from_spotify,
    get_tracks_for_playlist,
)
from app.services.user_auth_service import get_current_user_id
from app.utils import get_spotify_headers
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

router = APIRouter(tags=["playlists"])


@router.get("/playlists")
async def get_my_playlists(
    offset: int = Query(0),
    limit: int = Query(20, ge=1),
    db_session: Session = Depends(get_db),
) -> dict[str, str]:
    """
    Retrieve user's playlists from Spotify.

    Args:
        offset (int): The number of items to skip before starting to return results. Default is 0.
        limit (int): The maximum number of playlists to return. Must be at least 1. Default is 20.
        db_session (Session): The SQLAlchemy session to interact with the database.

    Returns:
        dict[str, str]: A dictionary containing the playlists retrieved from Spotify.
    """
    user_id = await get_current_user_id(db_session)
    return await get_my_playlists_from_spotify(user_id, offset, limit, db_session)


@router.post("/playlists")
async def create_playlist(
    playlist_name: str, db_session: Session = Depends(get_db)
) -> dict[str, str]:
    """
    Create a new playlist in the local database and on Spotify.

    Args:
        playlist_name (str): The name of the playlist to be created.
        db_session (Session): The SQLAlchemy session to interact with the database.

    Returns:
        dict[str, str]: A dictionary containing a success message.

    Raises:
        HTTPException: If there is an HTTP error when interacting with Spotify's API.
    """
    try:
        user_id = await get_current_user_id(db_session)
        tracks_db = get_tracks_for_playlist(db_session)
        playlist = create_playlist_in_db(playlist_name, tracks_db, db_session)
        spotify_headers = await get_spotify_headers(db_session)
        playlist_id = await create_playlist_on_spotify(user_id, playlist.name, spotify_headers)
        await add_tracks_to_playlist(
            playlist_id, [track.spotify_id for track in tracks_db], spotify_headers
        )
        return {"message": "Playlist created successfully."}

    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
