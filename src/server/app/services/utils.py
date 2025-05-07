import os
from random import choice
from string import ascii_letters, digits
from time import perf_counter

from dotenv import dotenv_values, find_dotenv
from fastapi import HTTPException, Request, status
from jose import jwt

env_path = find_dotenv()
config = dotenv_values(env_path)

if "PROD" in dict(os.environ).keys() and dict(os.environ)["PROD"] == "RAILWAY":
    config = dict(os.environ)


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
    """
    Asynchronous decorator to measure and print the execution time of an async function.

    Args:
        fn (Callable): The asynchronous function to be timed.

    Returns:
        Callable: A wrapped asynchronous function that prints execution time.

    Example:
        @time_it_async
        async def some_async_function():
            await asyncio.sleep(1)

    Notes:
        - This decorator prints the execution time of the function in seconds.
        - It should only be used with asynchronous functions.
    """

    async def inner(*args, **kwargs):
        start = perf_counter()
        result = await fn(*args, **kwargs)
        end = perf_counter()
        print(f"The {fn.__name__} took {end - start} seconds")
        return result

    return inner


def get_jwt_token(request: Request) -> str:
    """
    Extracts and validates a JWT access token from the request cookies.

    Args:
        request (Request): The FastAPI request object containing cookies.

    Returns:
        str: The decoded JWT access token.

    Raises:
        HTTPException: If the token is not found in cookies or if the token has expired (401).
    """
    token = request.cookies.get("access_token").removeprefix("Bearer ")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token not found")
    try:
        jwt.decode(token, config["SECRET_KEY"], algorithms=config["ALGORITHM"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="JWT token has expired"
        )

    return token.removeprefix("Bearer ")
