from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.playlists_service import (
    get_all_playlists,
    get_playlists_from_spotify,
    process_playlist_creation,
    retrieve_playlist_from_spotify_by_spotify_id,
)

router = APIRouter(tags=["playlists"], prefix="/playlists")


@router.get("")
async def get_playlists(
    offset: int = Query(0),
    limit: int = Query(20, ge=1),
    db_session: Session = Depends(get_db),
) -> dict:
    """
    Retrieve user's playlists from Spotify.

    Args:
        offset (int): The number of playlists to skip. Default is 0.
        limit (int): The maximum number of playlists to return. Must be at least 1. Default is 20.
        db_session (Session): The SQLAlchemy session to interact with the database.

    Returns:
        dict: A dictionary containing the playlists retrieved from Spotify.
    """
    return await get_playlists_from_spotify(offset, limit, db_session)


@router.get("/all")
async def get_all_spotify_playlists(db_session: Session = Depends(get_db)) -> dict:
    """
    Retrieve all Spotify playlists.

    Args:
        db_session (Session): The SQLAlchemy session to interact with the database.

    Returns:
        dict: A dictionary containing all playlists retrieved from Spotify.
    """
    return await get_all_playlists(db_session)


@router.get("/playlists/{id}")
async def get_playlist_by_spotify_id(
    spotify_id: str, db_session: Session = Depends(get_db)
) -> dict:
    """
    Retrieve a playlist from the database by its Spotify ID.

    Args:
        spotify_id (str): The Spotify ID of the playlist to retrieve.
        db_session (Session): The SQLAlchemy session to interact with the database.

    Returns:
        dict: A dictionary containing the retrieved playlist information.
    """
    return await retrieve_playlist_from_spotify_by_spotify_id(spotify_id, db_session)


@router.post("/create")
async def create_playlist(playlist_name: str, db_session: Session = Depends(get_db)) -> dict:
    """
    Create a new playlist in the local database and on Spotify.

    Args:
        playlist_name (str): The name of the playlist to be created.
        db_session (Session): The SQLAlchemy session to interact with the database.

    Returns:
        dict: A dictionary containing the result message.
    """
    return await process_playlist_creation(playlist_name, db_session)
