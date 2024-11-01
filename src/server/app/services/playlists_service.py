import asyncio
from itertools import chain

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import Playlist
from app.services.token_manager import get_spotify_headers
from app.services.tracks_service import fetch_listened_tracks
from app.services.user_auth_service import get_current_user_id
from app.services.utils import config


async def get_playlists_from_spotify(offset: int, limit: int, db_session: Session) -> dict:
    """
    Retrieve the current user's playlists from Spotify.

    Args:
        offset (int): The index of the first playlist to return.
        limit (int): The number of playlists to return.
        db_session (Session): The SQLAlchemy session to interact with the database.

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
            url = f"{config['SPOTIFY_API_URL']}/users/{user_id}/playlists?offset={offset}&limit={limit}"
            response = await client.get(url, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code, detail=exc.response.text
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc
        return response.json()


async def retrieve_playlist_from_spotify_by_spotify_id(
    spotify_id: str, db_session: Session
) -> dict:
    url = f"{config['SPOTIFY_API_URL']}/playlists/{spotify_id}"
    spotify_headers = await get_spotify_headers(db_session)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=spotify_headers)
        return response.json()["tracks"]["items"]


async def get_all_playlists(db_session: Session) -> dict:
    """
    Retrieve all playlists for the current user from Spotify by fetching in paginated batches.

    Args:
        db_session (Session): The SQLAlchemy session to interact with the database.

    Returns:
        dict: A dictionary containing the list of all user's playlists from Spotify.

    Raises:
        HTTPException: If any error occurs during the Spotify API requests, it raises an HTTPException
        with a specific status code and error details.
    """
    playlists = []
    offset, limit = 0, 50
    try:
        while True:
            response = await get_playlists_from_spotify(offset, limit, db_session)
            items = response.get("items", [])
            if not items:
                break
            playlists.extend(items)
            offset += limit
    except HTTPException as http_exc:
        raise http_exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc
    return {"playlists": playlists}


async def process_playlist_creation(playlist_name: str, db_session: Session) -> dict[str, str]:
    """
    Create a new playlist in the local database and on Spotify.
    The playlist will include tracks that are not included in any already existing one.

    Args:
        playlist_name (str): The name of the playlist to be created.
        db_session (Session): The SQLAlchemy session to interact with the database.

    Returns:
        dict[str, str]: A dictionary containing a success message.

    Raises:
        HTTPException: If there is an HTTP error when interacting with Spotify's API.
    """
    try:
        user_id, playlists, spotify_headers = await asyncio.gather(
            get_current_user_id(db_session),
            get_all_playlists(db_session),
            get_spotify_headers(db_session),
        )
        tracks = fetch_listened_tracks(db_session)
        playlist_tracks = await cache_playlist_tracks(playlists["playlists"], db_session)
        existing_track_titles = list(chain.from_iterable(playlist_tracks.values()))
        tracks_db = [track for track in tracks if track.title not in existing_track_titles]
        if not tracks_db:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No new tracks to be added to a playlist.",
            )
        playlist_id = await create_playlist_on_spotify(user_id, playlist_name, spotify_headers)
        create_playlist_in_db(playlist_name, playlist_id, tracks_db, db_session)
        await add_tracks_to_playlist(
            playlist_id, [track.spotify_id for track in tracks_db], spotify_headers
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc

    return {"message": f"The '{playlist_name}' playlist was created successfully."}


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


def create_playlist_in_db(
    playlist_name: str, playlist_id: str, tracks: list, db_session: Session
) -> Playlist:
    """
    Create a new playlist entry in the local database and associate it with the given tracks.

    Args:
        playlist_name (str): The name of the playlist.
        playlist_id (str): The ID of the playlist based on Spotify's playlist creation.
        tracks (list): A list of tracks to associate with the playlist.
        db_session (Session): SQLAlchemy session used for database operations.

    Returns:
        Playlist: The created playlist object.
    """
    playlist = Playlist(name=playlist_name, spotify_id=playlist_id, tracks=tracks)
    db_session.add(playlist)
    db_session.commit()
    return playlist


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
        response = await client.post(url, headers=spotify_headers, json=payload)
        response.raise_for_status()


async def cache_playlist_tracks(playlists, db_session) -> dict[str, set]:
    """
    Fetch all tracks for each playlist and store them in a cache dictionary.

    Args:
        playlists: List of playlists.
        db_session: The SQLAlchemy session.

    Returns:
        dict[str, set]: A dictionary with playlist IDs as keys and sets of track titles as values.
    """
    playlist_tracks_cache = {}
    spotify_headers = await get_spotify_headers(db_session)

    async def fetch_tracks(playlist):
        spotify_id = playlist["uri"].split(":")[-1]
        async with httpx.AsyncClient() as client:
            url = f"{config['SPOTIFY_API_URL']}/playlists/{spotify_id}"
            response = await client.get(url, headers=spotify_headers)
            response.raise_for_status()
            playlist_details = response.json()["tracks"]["items"]
            playlist_tracks_cache[spotify_id] = {item["track"]["name"] for item in playlist_details}

    await asyncio.gather(*[fetch_tracks(playlist) for playlist in playlists])
    return playlist_tracks_cache


async def is_track_in_any_playlist(track_title: str, playlist_tracks: dict[str, set]) -> bool:
    """
    Check if a track title exists in any playlist using the cached playlist tracks.

    Args:
        track_title (str): The title of the track.
        playlist_tracks_cache (dict[str, set]): Cached dictionary of playlist tracks.

    Returns:
        bool: True if the track is in any playlist, False otherwise.
    """
    return any(track_title in tracks for tracks in playlist_tracks.values())
