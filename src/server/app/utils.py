from random import choice
from string import ascii_letters, digits

from dotenv import dotenv_values, find_dotenv
from sqlalchemy.orm import Session

from app.token_manager import get_token

env_path = find_dotenv()
config = dotenv_values(env_path)


async def get_spotify_headers(db_session: Session) -> dict[str, str]:
    """
    Generate the headers required for Spotify API requests using the current access token.

    Args:
        db_session (Session): SQLAlchemy session used to retrieve the access token.

    Returns:
        dict[str, str]: A dictionary containing the Authorization header with the access token
        and Content-Type set to application/json.
    """
    token = get_token(db_session)
    return {
        "Authorization": f"Bearer {token['access_token']}",
        "Content-Type": "application/json",
    }


def generate_random_string(length: int) -> str:
    """
    Generate a random string of the specified length consisting of ASCII letters and digits.

    Args:
        length (int): The length of the generated string.

    Returns:
        str: A randomly generated string of the given length.
    """
    letters = ascii_letters + digits
    return "".join(choice(letters) for _ in range(length))
