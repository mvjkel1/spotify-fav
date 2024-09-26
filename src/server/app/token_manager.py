from time import time

import httpx
from app.db.models import AccessToken
from dotenv import dotenv_values, find_dotenv
from fastapi import status, HTTPException
from sqlalchemy.orm import Session

env_path = find_dotenv()
config = dotenv_values(env_path)


class TokenError(Exception):
    """Custom exception for token-related errors."""


class RefreshTokenError(Exception):
    """Custom exception for refresh token-related errors."""


def save_token(
    access_token: str, refresh_token: str, expires_in: int, db_session: Session
) -> None:
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


async def get_token(db_session: Session) -> dict:
    """
    Retrieve the current access token if it is still valid.

    Args:
        db_session (Session): The current database session.

    Returns:
        dict: A dictionary containing the token data.

    Raises:
        HTTPException: If the token does not exist (from the initial user login).
    """
    token = db_session.query(AccessToken).first()
    if not token or not token.access_token or not token.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are unauthorized, you have to login first.",
        )
    if token.expires_at > time():
        return {
            "access_token": token.access_token,
            "refresh_token": token.refresh_token,
            "expires_at": token.expires_at,
        }
    return await refresh_access_token(db_session, token.refresh_token)


async def refresh_access_token(db_session: Session, refresh_token: str) -> dict:
    """
    Refresh the access token using the refresh token.

    Args:
        db_session (Session): The current database session.

    Returns:
        dict: A dictionary containing the refreshed token data.
        None: If the refresh process fails.

    Raises:
        RefreshTokenError: If the refresh token is invalid or request fails.
        TokenError: If no valid token is available to refresh.
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
                f"Failed to refresh token: {e.response.status_code}, {e.response.text}"
            ) from exc
        except Exception as e:
            raise RefreshTokenError(f"Request failed: {str(e)}") from exc
