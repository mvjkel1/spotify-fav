import httpx
from app.db.models import Playlist, Track
from app.utils import get_spotify_headers
from dotenv import dotenv_values, find_dotenv
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

env_path = find_dotenv()
config = dotenv_values(env_path)


async def get_my_playlists_from_spotify(
    user_id: str, offset: int, limit: int, db_session: Session
) -> dict[str, str]:
    """
    Retrieve the current user's playlists from Spotify.

    Args:
        user_id (str): The Spotify user ID.
        offset (int): The index of the first playlist to return.
        limit (int): The number of playlists to return.
        db_session (Session): SQLAlchemy session used to obtain the Spotify headers.

    Returns:
        dict[str, str]: A JSON response from Spotify containing the user's playlists.

    Raises:
        HTTPException: If the Spotify API request fails, an HTTPException is raised with the
        status code and error details from the response.
    """
    headers = await get_spotify_headers(db_session)
    async with httpx.AsyncClient() as client:
        try:
            url = f"{config['SPOTIFY_API_URL']}/users/{user_id}/playlists?offset={offset}&limit={limit}"
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code, detail=exc.response.text
            ) from exc


async def create_playlist_on_spotify(
    user_id: str, playlist_name: str, spotify_headers: dict[str, str]
) -> str:
    """
    Create a new playlist on Spotify for the given user and return its Spotify ID.

    Args:
        user_id (str): The Spotify user ID.
        playlist_name (str): The name of the playlist.
        spotify_headers (dict[str, str]): Headers for the Spotify API request.

    Returns:
        str: The Spotify ID of the newly created playlist.

    Raises:
        HTTPException: If there is an error creating the playlist on Spotify, an HTTPException is
        raised with the status code and error details from the response.
    """
    url = f"{config['SPOTIFY_API_URL']}/users/{user_id}/playlists"
    payload = {"name": playlist_name}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=spotify_headers, json=payload)
        response.raise_for_status()
        return response.json()["id"]


async def add_tracks_to_playlist(
    playlist_id: str, track_ids: list[str], spotify_headers: dict[str, str]
) -> None:
    """
    Add tracks to a Spotify playlist.

    Args:
        playlist_id (str): The ID of the playlist to which tracks will be added.
        track_ids (list[str]): List of track IDs to add to the playlist.
        spotify_headers (dict[str, str]): Headers for the Spotify API request.

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
            raise HTTPException(
                status_code=exc.response.status_code, detail=exc.response.text
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc


def get_tracks_for_playlist(db_session: Session) -> list[Track]:
    """
    Fetch tracks from the database that have been listened to (i.e., have a nonzero listened count).

    Args:
        db_session (Session): SQLAlchemy session used for database operations.

    Returns:
        list[Track]: A list of tracks with a listened count greater than zero.
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
    return playlist
