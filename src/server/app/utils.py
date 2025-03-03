from random import choice
from string import ascii_letters, digits
from dotenv import dotenv_values, find_dotenv

env_path = find_dotenv()
config = dotenv_values(env_path)


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
