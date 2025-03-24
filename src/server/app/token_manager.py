from time import time

import httpx
from app.db.models import AccessToken
from app.utils import config
from fastapi import HTTPException, status
from sqlalchemy.orm import Session


class RefreshTokenError(Exception):
    """Custom exception for refresh token-related errors."""


def save_token(access_token: str, refresh_token: str, expires_in: int, db_session: Session) -> None:
    """
    Save or update the access and refresh tokens in the database.

    Args:
        access_token (str): The new access token.
        refresh_token (str): The refresh token.
        expires_in (int): Time in seconds until the access token expires.
        db_session (Session): The current database session.

    Returns:
        None
    """
    expires_at = time() + expires_in
    token = db_session.query(AccessToken).first()
    if token:
        token.access_token = access_token
        token.refresh_token = refresh_token
        token.expires_at = expires_at
    else:
        token = AccessToken(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )
        db_session.add(token)
    db_session.commit()


async def get_token(db_session: Session) -> dict[str, str]:
    """
    Retrieve the current access token if it is still valid, or refresh it.

    Args:
        db_session (Session): The current database session.

    Returns:
        dict: A dictionary containing the token data.

    Raises:
        HTTPException: If the token does not exist or refresh fails.
    """
    token = get_token_from_db(db_session)
    if not is_token_expired(token):
        return {
            "access_token": token.access_token,
            "refresh_token": token.refresh_token,
            "expires_at": token.expires_at,
        }
    return await handle_token_refresh(db_session, token.refresh_token)


def get_token_from_db(db_session: Session) -> AccessToken:
    """
    Retrieve the current token from the database.

    Args:
        db_session (Session): The current database session.

    Returns:
        AccessToken: The token object from the database.

    Raises:
        HTTPException: If the token is missing or invalid.
    """
    token = db_session.query(AccessToken).first()
    if not token or not token.access_token or not token.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token does not exist in the database, login first to generate one.",
        )
    return token


def is_token_expired(token: AccessToken) -> bool:
    """
    Check if the token is expired.

    Args:
        token (AccessToken): The token object to check.

    Returns:
        bool: True if the token is expired, False otherwise.
    """
    return token.expires_at < time()


async def handle_token_refresh(db_session: Session, refresh_token: str) -> dict[str, str]:
    """
    Handle the token refresh process.

    Args:
        db_session (Session): The current database session.
        refresh_token (str): The refresh token used to get a new access token.

    Returns:
        dict[str, str]: The refreshed token data.

    Raises:
        HTTPException: If the refresh process fails.
    """
    try:
        return await refresh_access_token(db_session, refresh_token)
    except RefreshTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token refresh failed: {str(exc)}"
        ) from exc


async def refresh_access_token(db_session: Session, refresh_token: str) -> dict[str, str]:
    """
    Refresh the access token using the refresh token.

    Args:
        db_session (Session): The current database session.
        refresh_token (str): The refresh token used to get a new access token.

    Returns:
        dict[str, str]: A dictionary containing the refreshed token data.

    Raises:
        RefreshTokenError: If the refresh token is invalid or an unexpected error occurs.
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
            new_token = {
                "access_token": token_data["access_token"],
                "refresh_token": refresh_token,
                "expires_at": token_data.get("expires_in", 3600),
            }
            save_token(*new_token.values(), db_session)
            return new_token
        except httpx.HTTPStatusError as exc:
            raise RefreshTokenError(
                f"Failed to refresh token: {exc.response.status_code}, {exc.response.text}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise RefreshTokenError("Request timed out while refreshing token") from exc
        except Exception as exc:
            raise RefreshTokenError(f"Unexpected error: {str(exc)}") from exc


async def get_spotify_headers(db_session: Session) -> dict[str, str]:
    """
    Generate the headers required for Spotify API requests using the current access token.

    Args:
        db_session (Session): SQLAlchemy session used to retrieve the access token.

    Returns:
        dict[str, str]: A dictionary containing the Authorization header with the access token
        and Content-Type set to application/json.
    """
    token = await get_token(db_session)
    return {
        "Authorization": f"Bearer {token['access_token']}",
        "Content-Type": "application/json",
    }
