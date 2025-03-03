from functools import wraps
from random import choice
from string import ascii_letters, digits
from dotenv import dotenv_values, find_dotenv
from fastapi import HTTPException
import httpx

from token_manager import token_manager

env_path = find_dotenv()
config = dotenv_values(env_path)


def refresh_token(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        access_token, refresh_token = token_manager.get_tokens()
        if access_token is None or refresh_token is None:
            raise HTTPException(
                status_code=401,
                detail="You have to login first to generate an access token.",
            )
        with httpx.Client() as client:
            response = client.get(
                "https://api.spotify.com/v1/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if response.status_code == 401:
            print(response)
            refresh_tokens_response = refresh_access_token(refresh_token)
            access_token = refresh_tokens_response["access_token"]
            token_manager.set_tokens(access_token, refresh_token)
        return func(*args, **kwargs)

    return wrapper


def refresh_access_token(refresh_token: str) -> dict:
    """
    Refresh the Spotify access token using the refresh token.
    """
    with httpx.Client() as client:
        response = client.post(
            config["SPOTIFY_TOKEN_URL"],
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": config["CLIENT_ID"],
                "client_secret": config["CLIENT_SECRET"],
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        return response.json()


@refresh_token
def get_spotify_headers() -> dict[str, str]:
    access_token, _ = token_manager.get_tokens()
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


def generate_random_string(length: int) -> str:
    """Generates a random string of the given length."""
    letters = ascii_letters + digits
    return "".join(choice(letters) for _ in range(length))
