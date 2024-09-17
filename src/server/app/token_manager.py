from time import time

import httpx
from sqlalchemy.orm import Session
from dotenv import dotenv_values, find_dotenv

from app.db.models import AccessToken

env_path = find_dotenv()
config = dotenv_values(env_path)


class TokenError(Exception):
    """Custom exception for token-related errors."""

    pass


class RefreshTokenError(Exception):
    """Custom exception for refresh token-related errors."""

    pass


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


def get_token(db_session: Session) -> dict | None:
    """
    Retrieve the current access token if it is still valid.

    Args:
        db_session (Session): The current database session.

    Returns:
        dict: A dictionary containing the token data if valid.
        None: If the token is invalid or expired, returns None.
    """
    token = db_session.query(AccessToken).first()

    if token and token.expires_at > time():
        return {
            "access_token": token.access_token,
            "refresh_token": token.refresh_token,
            "expires_at": token.expires_at,
        }

    return refresh_access_token(db_session) if token else None


async def refresh_access_token(db_session: Session) -> dict | None:
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
    token = get_token(db_session)

    if not token or not token["refresh_token"]:
        raise TokenError("No token to refresh was found, or the refresh token is invalid.")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                config["SPOTIFY_TOKEN_URL"],
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": token["refresh_token"],
                    "client_id": config["CLIENT_ID"],
                    "client_secret": config["CLIENT_SECRET"],
                },
            )
            if response.status_code == 200:
                token_data = response.json()
                save_token(
                    token_data["access_token"],
                    token["refresh_token"],
                    token_data.get("expires_in", 3600),
                    db_session,
                )
                return get_token(db_session)
            raise RefreshTokenError(
                f"Failed to refresh token: {response.status_code}, {response.text}"
            )
        except Exception as exc:
            raise RefreshTokenError(f"Request failed: {str(exc)}") from exc
