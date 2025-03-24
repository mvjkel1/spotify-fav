from random import choice
from string import ascii_letters, digits
from time import perf_counter

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


def time_it_async(fn):
    async def inner(*args, **kwargs):
        start = perf_counter()
        result = await fn(*args, **kwargs)
        end = perf_counter()
        print(f"The {fn.__name__} took {end - start} seconds")
        return result

    return inner
