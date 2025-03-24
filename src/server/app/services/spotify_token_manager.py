from datetime import datetime, timedelta, timezone
from time import time

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SpotifyAccessToken
from app.services.utils import config


async def save_spotify_token(
    access_token: str,
    refresh_token: str,
    expires_in: int,
    user_id: int,
    db_session: AsyncSession,
):
    """
    Save or update the access and refresh tokens in the database.

    Args:
        access_token (str): The new access token.
        refresh_token (str): The refresh token.
        expires_in (int): Time in seconds until the access token expires.
        user_id (int): The ID of logged in user.
        db_session (Session): The SQLAlchemy session to interact with the database.
    """
    expires_at = (datetime.now(tz=timezone.utc) + timedelta(seconds=expires_in)).timestamp()
    result = await db_session.execute(select(SpotifyAccessToken).filter_by(user_id=user_id))
    spotify_token = result.scalar_one_or_none()
    if spotify_token:
        spotify_token.access_token = access_token
        spotify_token.refresh_token = refresh_token
        spotify_token.expires_at = expires_at
    else:
        spotify_token = SpotifyAccessToken(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            user_id=user_id,
        )
        db_session.add(spotify_token)
    await db_session.commit()


async def get_spotify_token(user_id: int, db_session: AsyncSession) -> dict[str, str]:
    """
    Retrieve the current Spotify token if it is still valid, or refresh it.

    Args:
        user_id (int): The ID of logged in user.
        db_session (Session): The SQLAlchemy session to interact with the database.

    Returns:
        dict[str, str]: A dictionary containing the token data.

    Raises:
        HTTPException: If the token does not exist or refresh fails.
    """
    token = await get_spotify_token_from_db(user_id, db_session)
    if not token.is_expired():
        return {
            "access_token": token.access_token,
            "refresh_token": token.refresh_token,
            "expires_at": token.expires_at,
        }
    return await handle_spotify_token_refresh(token.refresh_token, user_id, db_session)


async def get_spotify_token_from_db(user_id: int, db_session: AsyncSession) -> SpotifyAccessToken:
    """
    Retrieve the Spotify access token from the database for a current user.

    Args:
        user_id (int): The ID of logged in user.
        db_session (Session): The SQLAlchemy session to interact with the database.

    Returns:
        AccessToken: The token object from the database.

    Raises:
        HTTPException: If the token is missing or invalid.
    """
    result = await db_session.execute(select(SpotifyAccessToken).filter_by(user_id=user_id))
    token = result.scalar_one_or_none()
    if not token or not token.access_token or not token.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Spotify access token does not exist in the database, login first to generate one.",
        )
    return token


async def handle_spotify_token_refresh(
    refresh_token: str, user_id: int, db_session: AsyncSession
) -> dict[str, str]:
    """
    Handle the token refresh process.

    Args:
        refresh_token (str): The refresh token used to get a new access token.
        user_id (int): The ID of logged in user.
        db_session (Session): The SQLAlchemy session to interact with the database.

    Returns:
        dict[str, str]: The refreshed token data.

    Raises:
        HTTPException: If the refresh process fails.
    """
    try:
        return await refresh_spotify_access_token(refresh_token, user_id, db_session)
    except HTTPException as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token refresh failed: {str(exc)}"
        ) from exc


async def refresh_spotify_access_token(
    refresh_token: str, user_id: int, db_session: AsyncSession
) -> dict[str, str]:
    """
    Refresh the access token using the refresh token.

    Args:
        refresh_token (str): The refresh token used to get a new access token.
        user_id (int): The ID of logged in user.
        db_session (Session): The SQLAlchemy session to interact with the database.

    Returns:
        dict[str, str]: A dictionary containing the refreshed token data.

    Raises:
        HTTPException: If the refresh token is invalid.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                config["SPOTIFY_TOKEN_URL"],
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": config["CLIENT_ID"],
                    "client_secret": config["CLIENT_SECRET"],
                },
            )
            response.raise_for_status()
            token_data = response.json()
            new_spotify_token = {
                "access_token": token_data["access_token"],
                "refresh_token": refresh_token,
                "expires_in": token_data.get("expires_in", 3600),
            }
            await save_spotify_token(*new_spotify_token.values(), user_id, db_session)
            return new_spotify_token
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                f"Failed to refresh token: {exc.response.status_code} - {exc.response.text}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise HTTPException("Request timed out while refreshing token") from exc


async def get_spotify_headers(user_id: int, db_session: AsyncSession) -> dict[str, str]:
    """
    Generate the headers required for Spotify API requests using the current access token.

    Args:
        user_id (int): The ID of logged in user.
        db_session (Session): SQLAlchemy session used to retrieve the access token.

    Returns:
        dict[str, str]: A dictionary containing the Authorization header with the access token
                        and Content-Type set to application/json.
    """
    spotify_token = await get_spotify_token(user_id, db_session)
    return {
        "Authorization": f"Bearer {spotify_token.get("access_token")}",
        "Content-Type": "application/json",
    }
