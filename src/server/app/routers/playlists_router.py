from app.db.database import get_db
from app.services.playlists_service import get_my_playlists_from_spotify, process_playlist_creation
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

router = APIRouter(tags=["playlists"])


@router.get("/playlists")
async def get_my_playlists(
    offset: int = Query(0),
    limit: int = Query(20, ge=1),
    db_session: Session = Depends(get_db),
) -> dict:
    """
    Retrieve user's playlists from Spotify.

    Args:
        offset (int): The number of items to skip before starting to return results. Default is 0.
        limit (int): The maximum number of playlists to return. Must be at least 1. Default is 20.
        db_session (Session): The SQLAlchemy session to interact with the database.

    Returns:
        dict: A dictionary containing the playlists retrieved from Spotify.
    """
    return await get_my_playlists_from_spotify(offset, limit, db_session)


@router.post("/playlists")
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
