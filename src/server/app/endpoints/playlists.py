import httpx
from app.db.database import get_db
from dotenv import dotenv_values, find_dotenv
from app.endpoints.user_auth import get_current_user_id
from fastapi import APIRouter, Depends, HTTPException
from app.db.models import Playlist, Track
from sqlalchemy.orm import Session
from app.token_manager import get_token
from app.utils import get_spotify_headers

env_path = find_dotenv()
config = dotenv_values(env_path)
router = APIRouter(tags=["playlists"])


@router.get("/playlists")
async def get_my_playlists(db_session: Session = Depends(get_db)) -> dict:
    """
    Retrieve the current user's playlists from Spotify.

    Args:
        db_session (Session): SQLAlchemy session used to obtain the Spotify headers.

    Returns:
        dict: A JSON response from Spotify containing the user's playlists.

    Raises:
        HTTPException: If the Spotify API request fails, an HTTPException is raised with the
        status code and error details from the response.
    """
    headers = await get_spotify_headers(db_session)
    async with httpx.AsyncClient() as client:
        try:
            user_id = await get_current_user_id(db_session)
            url = f"{config['SPOTIFY_API_URL']}/users/{user_id}/playlists"
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)


@router.post("/playlists")
async def create_playlist(playlist_name: str, db_session: Session = Depends(get_db)) -> dict:
    """
    Create a new playlist both locally in the database and remotely on Spotify,
    and populate it with tracks.

    Args:
        playlist_name (str): The name of the playlist to create.
        db_session (Session): SQLAlchemy session used for database operations.

    Returns:
        dict: A confirmation message indicating that the playlist was created successfully.

    Raises:
        HTTPException: If there is an error during the playlist creation process,
        an HTTPException is raised with the status code and error details from the response.
    """
    try:
        token = get_token(db_session)
        user_id = await get_current_user_id()
        tracks_db = get_tracks_for_playlist(db_session)
        playlist = create_playlist_in_db(playlist_name, tracks_db, db_session)
        spotify_headers = await get_spotify_headers(db_session)
        playlist_id = await create_playlist_on_spotify(
            user_id, playlist, token["access_token"], spotify_headers
        )
        await add_tracks_to_playlist(
            playlist_id, [track.spotify_id for track in tracks_db], spotify_headers
        )
        return {"message": "Playlist created successfully."}
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def get_tracks_for_playlist(db_session: Session) -> list:
    """
    Fetch tracks from the database that have been listened to (i.e., have a nonzero listened count).

    Args:
        db_session (Session): SQLAlchemy session used for database operations.

    Returns:
        list: A list of tracks with a listened count greater than zero.
    """
    return db_session.query(Track).filter(Track.listened_count > 0).all()


def create_playlist_in_db(playlist_name: str, tracks: list, db_session: Session) -> Playlist:
    """
    Create a new playlist entry in the local database and associate it with the given tracks.

    Args:
        playlist_name (str): The name of the playlist.
        tracks (list): A list of tracks to associate with the playlist.
        db_session (Session): SQLAlchemy session used for database operations.

    Returns:
        Playlist: The created playlist object.
    """
    playlist = Playlist(name=playlist_name, tracks=tracks)
    db_session.add(playlist)
    db_session.commit()
    db_session.close()
    return playlist


async def create_playlist_on_spotify(user_id: str, playlist: Playlist, spotify_headers) -> str:
    """
    Create a new playlist on Spotify for the given user and return its Spotify ID.

    Args:
        user_id (str): The Spotify user ID.
        playlist (Playlist): The playlist object containing the name and other details.
        spotify_headers: Headers for the Spotify API request.

    Returns:
        str: The Spotify ID of the newly created playlist.

    Raises:
        HTTPException: If there is an error creating the playlist on Spotify, an HTTPException is
        raised with the status code and error details from the response.
    """
    url = f"{config['SPOTIFY_API_URL']}/users/{user_id}/playlists"
    payload = {"name": playlist.name}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=spotify_headers, json=payload)
        response.raise_for_status()
        return response.json()["id"]


async def add_tracks_to_playlist(playlist_id: str, track_ids: list[str], spotify_headers) -> None:
    """
    Add tracks to a Spotify playlist.

    Args:
        playlist_id (str): The ID of the playlist to which tracks will be added.
        track_ids (list[str]): List of track IDs to add to the playlist.
        spotify_headers: Headers for the Spotify API request.

    Raises:
        HTTPException: If the Spotify API request fails, an HTTPException is raised with the
        status code and error details from the response.
    """
    url = f"{config['SPOTIFY_API_URL']}/playlists/{playlist_id}/tracks"
    track_uris = [f"spotify:track:{track_id}" for track_id in track_ids]
    payload = {"uris": track_uris}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=spotify_headers, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))