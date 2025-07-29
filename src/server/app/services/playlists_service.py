import asyncio
import hashlib
from itertools import chain

import httpx
from app.db.models import Playlist, Track
from app.services.spotify_auth_service import get_current_spotify_user_id
from app.services.spotify_token_manager import get_spotify_headers
from app.services.tracks_service import fetch_listened_tracks
from app.services.user_auth_service import get_current_user_db
from app.services.utils import config
from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio.session import AsyncSession
from upstash_redis.asyncio import Redis

MAX_PLAYLIST_TRACKS = 100


async def get_playlists_from_spotify(
    offset: int, limit: int, user_id: int, db_session: AsyncSession
) -> dict:
    """
    Retrieve the current user's playlists from Spotify.

    Args:
        offset (int): The index of the first playlist to return.
        limit (int): The number of playlists to return.
        user_id (int): The ID of logged in user.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.

    Returns:
        dict: A JSON response from Spotify containing the user's playlists.

    Raises:
        HTTPException: If the Spotify API request fails, an HTTPException is raised with
                       the status code and error details from the response.
    """
    spotify_headers = await get_spotify_headers(user_id, db_session)
    async with httpx.AsyncClient() as client:
        try:
            user = await get_current_user_db(user_id, db_session)
            url = f"{config['SPOTIFY_API_URL']}/users/{user.spotify_uid}/playlists?offset={offset}&limit={limit}"
            response = await client.get(url, headers=spotify_headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=f"Failed to retrieve spotify playlists.",
            ) from exc

        return response.json()


async def retrieve_playlist_from_spotify_by_playlist_id(
    spotify_id: str, user_id: int, db_session: AsyncSession
) -> dict:
    """
    Retrieve the tracks of a Spotify playlist using its Spotify ID.

    Args:
        spotify_id (str): The Spotify ID of the playlist to retrieve.
        user_id (int): The ID of logged in user.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.

    Returns:
        dict: A dictionary containing tracks from the specified playlist.
    """
    url = f"{config['SPOTIFY_API_URL']}/playlists/{spotify_id}"
    spotify_headers = await get_spotify_headers(user_id, db_session)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=spotify_headers)
        return response.json()


async def sync_playlists(user_id: int, db_session: AsyncSession) -> None:
    """
    Synchronize spotify-fav playlists between database and Spotify.

    Args:
        user_id (int): The ID of logged in user.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.
    """
    db_playlists_ids = await get_db_playlist_ids(db_session)
    spotify_playlists_ids = await get_spotify_playlist_ids(user_id, db_session)
    await remove_unmatched_playlists(db_playlists_ids, spotify_playlists_ids, db_session)


async def get_db_playlist_ids(db_session: AsyncSession) -> set[str]:
    """
    Retrieve Spotify playlist IDs stored in the database.

    Args:
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.

    Returns:
        set[str]: A set of Spotify playlist IDs from the database.
    """
    result = await db_session.execute(select(Playlist))
    db_playlists = result.scalars().all()
    return {playlist.spotify_id for playlist in db_playlists}


async def get_spotify_playlist_ids(user_id: int, db_session: AsyncSession) -> set[str]:
    """
    Fetch Spotify playlist IDs for the user that contain 'spotify_fav' in their names.

    Args:
        user_id (int): The ID of the logged-in user.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.

    Returns:
        set[str]: A set of Spotify playlist IDs retrieved from the user's account.
    """
    spotify_playlists = await get_all_playlists(user_id, db_session)
    return {
        playlist["id"]
        for playlist in next(iter(spotify_playlists.values()), [])
        if "spotify_fav" in playlist["name"]
    }


async def remove_unmatched_playlists(
    db_playlists_ids: set[str], spotify_playlists_ids: set[str], db_session: AsyncSession
) -> None:
    """
    Remove playlists from the database that are no longer present in the user's Spotify account.

    Args:
        db_playlists_ids (set[str]): A set of playlist IDs currently in the database.
        spotify_playlists_ids (set[str]): A set of playlist IDs fetched from Spotify.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.
    """
    playlists_to_remove_ids = db_playlists_ids - spotify_playlists_ids
    if playlists_to_remove_ids:
        await db_session.execute(
            delete(Playlist).where(Playlist.spotify_id.in_(playlists_to_remove_ids))
        )
        await db_session.commit()


async def get_all_playlists(user_id: int, db_session: AsyncSession) -> dict:
    """
    Retrieve all playlists for the current user from Spotify by fetching in batches.

    Args:
        user_id (int): The ID of logged in user.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.

    Returns:
        dict: A dictionary containing the list of all user's playlists from Spotify.

    Raises:
        HTTPException: If any error occurs during the Spotify API requests, it raises an HTTPException
        with a specific status code and error details.
    """
    playlists, offset, limit = [], 0, 50
    try:
        while True:
            response = await get_playlists_from_spotify(offset, limit, user_id, db_session)
            if not (items := response.get("items")):
                break
            playlists.extend(items)
            offset += limit
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc

    return {"playlists": playlists}


async def filter_new_tracks(playlists: dict, user_id: int, db_session: AsyncSession) -> list[Track]:
    """
    Filter out tracks that are already included in existing playlists.

    Args:
        playlists (dict): A dictionary containing existing playlists and their tracks.
        user_id (int): The ID of logged in user.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.

    Returns:
        list: A list of tracks that are new and not included in any existing playlists.
    """
    tracks = await fetch_listened_tracks(user_id, db_session)
    playlists_tracks = await cache_playlists_tracks(playlists["playlists"], user_id, db_session)
    existing_track_titles = list(chain.from_iterable(playlists_tracks.values()))
    return [track for track in tracks if track.title not in existing_track_titles]


async def create_playlist(
    playlist_name: str,
    tracks_db: list,
    spotify_user_id: str,
    user_id: int,
    db_session: AsyncSession,
    spotify_headers: dict,
) -> None:
    """
    Create a new playlist on Spotify and store it in the local database.

    Args:
        playlist_name (str): The name of the playlist to be created.
        tracks_db (list): A list of track objects to be added to the playlist.
        spotify_user_id (str): The Spotify user ID.
        user_id (int): The ID of logged in user.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.
        spotify_headers (dict): The headers for Spotify API requests.
    """
    playlist_id = await create_playlist_on_spotify(spotify_user_id, playlist_name, spotify_headers)
    await create_playlist_in_db(playlist_name, playlist_id, tracks_db, user_id, db_session)
    await add_tracks_to_playlist(
        playlist_id, [track.spotify_id for track in tracks_db], spotify_headers
    )


async def process_playlist_creation(
    playlist_name: str, user_id: int, db_session: AsyncSession
) -> dict[str, str]:
    """
    Create a new playlist in the local database and on Spotify.
    The playlist will include tracks that are not included in any already existing one.

    Args:
        playlist_name (str): The name of the playlist to be created.
        user_id (int): The ID of logged in user.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.

    Returns:
        dict[str, str]: A dictionary containing a success message.

    Raises:
        HTTPException: If there is an HTTP error when interacting with Spotify's API.
    """
    try:
        await sync_playlists(user_id, db_session)
        spotify_user_id = await get_current_spotify_user_id(user_id, db_session)
        playlists = await get_all_playlists(user_id, db_session)
        spotify_headers = await get_spotify_headers(user_id, db_session)
        tracks_db = await filter_new_tracks(playlists, user_id, db_session)
        if not tracks_db:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The playlist cannot be created since there are no new tracks listened recently.",
            )
        await create_playlist(
            playlist_name,
            tracks_db[:MAX_PLAYLIST_TRACKS],
            spotify_user_id,
            user_id,
            db_session,
            spotify_headers,
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc

    return {"message": f"The '{playlist_name}' playlist was created successfully."}


async def create_playlist_on_spotify(
    spotify_user_id: str, playlist_name: str, spotify_headers: dict[str, str]
) -> str:
    """
    Create a new playlist on Spotify for the given user and return its Spotify ID.

    Args:
        spotify_user_id (str): The Spotify user ID.
        playlist_name (str): The name of the playlist.
        spotify_headers (dict[str, str]): Headers for the Spotify API request.

    Returns:
        str: The Spotify ID of the newly created playlist.

    Raises:
        HTTPException: If there is an error creating the playlist on Spotify, an HTTPException is
        raised with the status code and error details from the response.
    """
    url = f"{config['SPOTIFY_API_URL']}/users/{spotify_user_id}/playlists"
    playlist_name = f"{playlist_name}_spotify_fav"
    payload = {"name": playlist_name}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=spotify_headers, json=payload)
        response.raise_for_status()
        return response.json()["id"]


async def create_playlist_in_db(
    playlist_name: str, playlist_id: str, tracks: list, user_id: int, db_session: AsyncSession
) -> Playlist:
    """
    Create a new playlist entry in the local database and associate it with the given tracks.

    Args:
        playlist_name (str): The name of the playlist.
        playlist_id (str): The ID of the playlist based on Spotify's playlist creation.
        tracks (list): A list of tracks to associate with the playlist.
        user_id (int): The ID of logged in user.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.

    Returns:
        Playlist: The created playlist object.
    """
    playlist = Playlist(name=playlist_name, spotify_id=playlist_id, tracks=tracks, user_id=user_id)
    db_session.add(playlist)
    await db_session.commit()
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


async def cache_playlists_tracks(
    playlists: list[dict], user_id: int, db_session: AsyncSession
) -> dict[str, set[str]]:
    """
    Caches tracks for multiple Spotify playlists in Redis.

    Args:
        playlists (list[dict]): List of Spotify playlist dictionaries.
        user_id (int): ID of the current user.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.

    Returns:
        dict[str, set[str]]: Mapping of playlist IDs to sets of track titles.
    """
    redis = Redis(
        url=config["REDIS_URL"],
        token=config["REDIS_TOKEN"],
    )
    cache = {}

    await asyncio.gather(
        *[process_playlist_cache(p, user_id, redis, cache, db_session) for p in playlists]
    )

    await redis.close()
    return cache


async def process_playlist_cache(
    playlist: dict, user_id: int, redis: Redis, cache: dict[str, set[str]], db_session: AsyncSession
) -> None:
    """
    Checks if a playlist's track list in Redis is up to date.
    If stale, fetches updated tracks from Spotify and refreshes the cache.

    Args:
        playlist (dict): Playlist dictionary containing metadata.
        user_id (int): ID of the current user.
        redis (Redis): Redis client.
        cache (dict): Dictionary to store track sets by playlist ID.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.
    """
    spotify_playlist_id = get_spotify_playlist_id(playlist)
    cache_key = build_cache_key(spotify_playlist_id, user_id)
    cached_tracks = await get_cached_playlist(redis, cache_key)
    if cached_tracks:
        cache[spotify_playlist_id] = cached_tracks
        return

    fresh_tracks = await get_playlist_tracks(spotify_playlist_id, user_id, db_session)
    await update_cache(redis, cache_key, fresh_tracks)
    cache[spotify_playlist_id] = fresh_tracks


def get_spotify_playlist_id(playlist: dict) -> str:
    """
    Extracts the Spotify playlist ID from its URI.

    Args:
        playlist (dict): Playlist details dictionary.

    Returns:
        str: Spotify playlist ID.
    """
    return playlist["uri"].split(":")[-1]


def build_cache_key(spotify_id: str, user_id: int) -> tuple[str, str]:
    """
    Builds Redis keys for a playlist's tracks data.

    Args:
        spotify_id (str): Spotify playlist ID.
        user_id (int): User ID.

    Returns:
        tuple[str, str]: Redis playlist tracks list key.
    """
    return f"playlist:{spotify_id}:{user_id}:tracks"


def generate_hash(tracks: set[str]) -> str:
    """
    Generates a hash to detect changes in the playlist's track list.

    Args:
        tracks (set[str]): Set of track titles.

    Returns:
        str: SHA-256 hash of the sorted track list.
    """
    return hashlib.sha256(",".join(sorted(tracks)).encode()).hexdigest()


def serialize_tracks(tracks: set[str]) -> str:
    """
    Serializes a set of track names into a Redis-storable string.

    Args:
        tracks (set[str]): Track titles.

    Returns:
        str: Serialized string.
    """
    return ")%(".join(tracks)


def deserialize_tracks(raw: str | None) -> set[str]:
    """
    Deserializes a Redis-stored string into a set of track names.

    Args:
        raw (str | None): Raw cached string.

    Returns:
        set[str]: Set of track titles.
    """
    return set(raw.split(")%(")) if raw else set()


async def get_cached_playlist(
    redis: Redis, cache_key: SyntaxWarning
) -> tuple[set[str], str | None]:
    """
    Retrieves the cached playlist tracks from Redis.

    Args:
        redis (Redis): Redis client.
        cache_key (str): Redis key for track data.

    Returns:
        tuple[set[str]]: Cached tracks.
    """
    raw_tracks = await redis.get(cache_key)
    return deserialize_tracks(raw_tracks)


async def get_playlist_tracks(
    spotify_playlist_id: str, user_id: int, db_session: AsyncSession
) -> set[str]:
    """
    Fetches the latest set of track names from the Spotify API for a given playlist.

    Args:
        spotify_playlist_id (str): Spotify playlist ID.
        user_id (int): User ID.
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.

    Returns:
        set[str]: Set of track titles.
    """
    playlist = await retrieve_playlist_from_spotify_by_playlist_id(
        spotify_playlist_id, user_id, db_session
    )
    return {item["track"]["name"] for item in playlist["tracks"]["items"]}


def should_use_cache(cached_hash: str | None, new_hash: str) -> bool:
    """
    Compares cached hash with a new hash to determine cache validity.

    Args:
        cached_hash (str | None): Previously cached hash.
        new_hash (str): Newly computed hash.

    Returns:
        bool: True if cache is valid (no changes), False otherwise.
    """
    return cached_hash == new_hash


async def update_cache(redis: Redis, cache_key: str, tracks: set[str]) -> None:
    """
    Stores updated playlist tracks data in Redis.

    Args:
        redis (Redis): Redis client.
        cache_key (str): Key for track list.
        tracks (set[str]): Set of current track titles.
    """
    await redis.set(cache_key, serialize_tracks(tracks), ex=3600)
