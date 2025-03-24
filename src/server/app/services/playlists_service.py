import asyncio
from itertools import chain

import httpx
from app.db.models import Playlist, Track
from app.services.token_manager import get_spotify_headers
from app.services.tracks_service import fetch_listened_tracks
from app.services.user_auth_service import get_current_user_id
from app.services.utils import config
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from upstash_redis.asyncio import Redis


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
    """
    Retrieve the tracks of a Spotify playlist using its Spotify ID.

    Args:
        spotify_id (str): The Spotify ID of the playlist to retrieve.
        db_session (Session): The SQLAlchemy session to interact with the database.

    Returns:
        dict: A dictionary containing tracks from the specified playlist.
    """
    url = f"{config['SPOTIFY_API_URL']}/playlists/{spotify_id}"
    spotify_headers = await get_spotify_headers(db_session)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=spotify_headers)
        return response.json()


async def sync_playlists(db_session: Session) -> None:
    """
    Synchronize spotify-fav playlists between database and the Spotify.

    Args:
        db_session (Session): The SQLAlchemy session to interact with the database.

    Returns:
        None
    """
    db_playlists_ids = {playlist.spotify_id for playlist in db_session.query(Playlist).all()}
    spotify_playlists = await get_all_playlists(db_session)
    spotify_playlists_ids = {
        playlist["id"]
        for playlist in list(spotify_playlists.values())[0]
        if "spotify_fav" in playlist["name"]
    }
    playlists_to_remove_ids = db_playlists_ids - spotify_playlists_ids
    db_session.query(Playlist).filter(Playlist.spotify_id.in_(playlists_to_remove_ids)).delete()
    db_session.commit()


async def get_all_playlists(db_session: Session) -> dict:
    """
    Retrieve all playlists for the current user from Spotify by fetching in batches.

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


async def filter_new_tracks(db_session: Session, playlists: dict) -> list[Track]:
    """
    Filter out tracks that are already included in existing playlists.

    Args:
        db_session (Session): The SQLAlchemy session to interact with the database.
        playlists (dict): A dictionary containing existing playlists and their tracks.

    Returns:
        list: A list of tracks that are new and not included in any existing playlists.
    """
    tracks = fetch_listened_tracks(db_session)
    playlist_tracks = await cache_playlist_tracks(playlists["playlists"], db_session)
    existing_track_titles = list(chain.from_iterable(playlist_tracks.values()))
    return [track for track in tracks if track.title not in existing_track_titles]


async def create_playlist(
    playlist_name: str, tracks_db: list, user_id: str, db_session: Session, spotify_headers: dict
) -> None:
    """
    Create a new playlist on Spotify and store it in the local database.

    Args:
        playlist_name (str): The name of the playlist to be created.
        tracks_db (list): A list of track objects to be added to the playlist.
        user_id (str): The Spotify user ID.
        db_session (Session): The SQLAlchemy session to interact with the database.
        spotify_headers (dict): The headers for Spotify API requests.

    Returns:
        None
    """
    playlist_id = await create_playlist_on_spotify(user_id, playlist_name, spotify_headers)
    create_playlist_in_db(playlist_name, playlist_id, tracks_db, db_session)
    await add_tracks_to_playlist(
        playlist_id, [track.spotify_id for track in tracks_db], spotify_headers
    )


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
        await sync_playlists(db_session)
        user_id, playlists, spotify_headers = await asyncio.gather(
            get_current_user_id(db_session),
            get_all_playlists(db_session),
            get_spotify_headers(db_session),
        )
        tracks_db = await filter_new_tracks(db_session, playlists)
        if not tracks_db:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The playlist cannot be created since there are no new tracks listened recently.",
            )
        await create_playlist(playlist_name, tracks_db, user_id, db_session, spotify_headers)
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
    playlist_name = f"{playlist_name}_spotify_fav"
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
        db_session (Session): The SQLAlchemy session to interact with the database.

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


async def cache_playlist_tracks(playlists: list[dict], db_session: Session) -> dict[str, set]:
    """
    Fetch all tracks for each playlist and store them in a cache (Redis).

    Args:
        playlists (list[dict]): List of dictonaries containing the playlists details.
        db_session (Session): The SQLAlchemy session to interact with the database.

    Returns:
        dict[str, set]: A dictionary with playlist IDs as keys and sets of track titles as values.
    """
    playlist_tracks_cache = {}
    spotify_headers = await get_spotify_headers(db_session)
    redis_client = Redis(
        url=config["REDIS_URL"],
        token=config["REDIS_TOKEN"],
    )

    async def fetch_tracks(playlist: dict):
        """
        Fetch tracks for a given playlist from the Spotify API.

        This inner asynchronous function retrieves track information for a
        specific playlist identified by its Spotify ID and updates the
        `playlist_tracks_cache` with the track names.

        Args:
            playlist (dict): A dictionary containing the details of the playlist.

        Raises:
            httpx.HTTPStatusError: If the request to the Spotify API fails.
        """
        spotify_id = playlist["uri"].split(":")[-1]
        cache_key = f"playlist:{spotify_id}:tracks"
        cached_tracks = await redis_client.get(cache_key)
        if cached_tracks:
            playlist_tracks_cache[spotify_id] = set(cached_tracks.split(","))
            return

        async with httpx.AsyncClient() as client:
            url = f"{config['SPOTIFY_API_URL']}/playlists/{spotify_id}"
            response = await client.get(url, headers=spotify_headers)
            response.raise_for_status()
            playlist_details = response.json()["tracks"]["items"]
            tracks = {item["track"]["name"] for item in playlist_details}
            await redis_client.set(cache_key, ",".join(tracks), ex=3600)
            playlist_tracks_cache[spotify_id] = tracks

    await asyncio.gather(*[fetch_tracks(playlist) for playlist in playlists])
    await redis_client.close()
    return playlist_tracks_cache
