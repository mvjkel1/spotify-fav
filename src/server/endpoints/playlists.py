import httpx
from dotenv import dotenv_values, find_dotenv
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import SessionLocal, get_db
from endpoints.user_auth import get_current_user_id
from models import Playlist, Track
from token_manager import token_manager
from utils import get_spotify_headers, refresh_token

env_path = find_dotenv()
config = dotenv_values(env_path)

router = APIRouter(tags=["playlists"])


@refresh_token
@router.get("/playlists")
async def get_my_playlists() -> dict:
    """
    Retrieve the current user's playlists from Spotify.

    Args:
        access_token (str): OAuth token for Spotify API.

    Returns:
        dict: JSON response from Spotify containing the playlists.

    Raises:
        HTTPException: If the Spotify API request fails.
    """
    headers = get_spotify_headers()
    async with httpx.AsyncClient() as client:
        try:
            user_id = await get_current_user_id()
            url = f"{config['SPOTIFY_API_URL']}/users/{user_id}/playlists"
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)


@refresh_token
@router.post("/playlists")
async def create_playlist(playlist_name: str, db_session: Session = Depends(get_db)) -> dict:
    """
    Create a new playlist both locally in the database and remotely on Spotify,
    and populate it with tracks.

    Args:
        playlist_name (str): The name of the playlist to create.
        db_session (Session): SQLAlchemy session for database operations.

    Returns:
        dict: Confirmation message that the playlist was created.

    Raises:
        HTTPException: If there is an error during the playlist creation process.
    """
    try:
        access_token, _ = token_manager.get_tokens()
        user_id = await get_current_user_id(access_token)
        tracks_db = get_tracks_for_playlist(db_session)
        playlist = create_playlist_in_db(playlist_name, tracks_db, db_session)
        playlist_id = await create_playlist_on_spotify(user_id, playlist, access_token)
        await add_tracks_to_playlist(
            playlist_id, [track.spotify_id for track in tracks_db], access_token
        )
        return {"message": "Playlist created successfully."}
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def get_tracks_for_playlist(db_session: Session = Depends(get_db)) -> list:
    """
    Fetch tracks from the database that have been listened to (i.e., have a non-zero listened count).

    Args:
        db_session (Session): SQLAlchemy session for database operations.

    Returns:
        list: A list of tracks with a listened count greater than zero.
    """
    return db_session.query(Track).filter(Track.listened_count > 0).all()


def create_playlist_in_db(
    playlist_name: str, tracks: list, db_session: Session = Depends(get_db)
) -> Playlist:
    """
    Create a new playlist entry in the local database and associate it with the given tracks.

    Args:
        playlist_name (str): The name of the playlist.
        tracks (list): A list of tracks to associate with the playlist.
        db_session (Session): SQLAlchemy session for database operations.

    Returns:
        Playlist: The created playlist object.
    """
    playlist = Playlist(name=playlist_name, tracks=tracks)
    db_session.add(playlist)
    db_session.commit()
    db_session.close()
    return playlist


async def create_playlist_on_spotify(user_id: str, playlist: Playlist) -> str:
    """
    Create a new playlist on Spotify for the given user and return its Spotify ID.

    Args:
        user_id (str): The Spotify user ID.
        playlist (Playlist): The playlist object containing the name and other details.

    Returns:
        str: The Spotify ID of the newly created playlist.

    Raises:
        HTTPException: If there is an error creating the playlist on Spotify.
    """
    url = f"{config['SPOTIFY_API_URL']}/users/{user_id}/playlists"
    headers = get_spotify_headers()
    payload = {"name": playlist.name}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["id"]


async def add_tracks_to_playlist(playlist_id: str, track_ids: list[str]) -> None:
    """
    Add tracks to a Spotify playlist.

    Args:
        playlist_id (str): The ID of the playlist to which tracks will be added.
        track_ids (list[str]): List of track IDs to add to the playlist.
        access_token (str): OAuth token for Spotify API.

    Raises:
        HTTPException: If the Spotify API request fails.
    """
    url = f"{config['SPOTIFY_API_URL']}/playlists/{playlist_id}/tracks"
    headers = get_spotify_headers()
    track_uris = [f"spotify:track:{track_id}" for track_id in track_ids]
    payload = {"uris": track_uris}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
