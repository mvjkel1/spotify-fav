from typing import Annotated
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from passlib.context import CryptContext
from fastapi import status
from app.db.schemas import TokenData, UserRegister
from datetime import datetime, timezone, timedelta
from app.services.utils import config
from jose import JWTError, jwt
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from app.db.database import async_get_db
from app.db.schemas import UserSchema

OAUTH2_SCHEME = OAuth2PasswordBearer(tokenUrl="/user-auth/token")
PWD_CONTEXT = CryptContext(schemes=["argon2"], deprecated="auto")


async def handle_user_register(
    user: UserRegister,
    db_session: AsyncSession,
) -> dict:
    """
    Handles the user registration process.

    Args:
        db_session (Session): The database session.
        user (UserRegister): The user registration data, including email and password.

    Raises:
        HTTPException: If the email is already registered.

    Returns:
        dict: A dictionary containing a success message and the email of the newly registered user.
    """
    existing_user = await get_user_by_email(db_session, user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )
    hashed_password = hash_password(user.password)
    new_user = User(email=user.email, hashed_password=hashed_password)
    db_session.add(new_user)
    await db_session.commit()
    await db_session.refresh(new_user)
    return {"message": "User registered successfully", "email": new_user.email}


def create_token(data: dict, secret_key: str, expires_delta: timedelta) -> str:
    """
    Generates a JSON Web Token (JWT).

    Args:
        data (dict): The payload data to include in the token.
        secret_key (str): The secret key used to sign the token.
        expires_delta (timedelta): The duration until the token expires.

    Returns:
        str: The encoded JWT as a string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=config["ALGORITHM"])
    return encoded_jwt


def create_access_token(data: dict) -> str:
    """
    Creates an access token with a predefined expiration time.

    Args:
        data (dict): The payload data to include in the token.

    Returns:
        str: The encoded access token.
    """
    return create_token(
        data, config["SECRET_KEY"], timedelta(minutes=int(config["ACCESS_TOKEN_EXPIRE_MINUTES"]))
    )


def create_refresh_token(data: dict) -> str:
    """
    Creates a refresh token with a predefined expiration time.

    Args:
        data (dict): The payload data to include in the token.

    Returns:
        str: The encoded refresh token.
    """
    return create_token(
        data, config["SECRET_KEY"], timedelta(days=int(config["REFRESH_TOKEN_EXPIRE_DAYS"]))
    )


def hash_password(password: str) -> str:
    """
    Hashes a plain text password using the configured hashing algorithm.

    Args:
        password (str): The plain text password to hash.

    Returns:
        str: The hashed password.
    """
    return PWD_CONTEXT.hash(password)


async def get_user_by_email(db_session: AsyncSession, email: str) -> User | None:
    """
    Retrieves a user from the database by their email address.

    Args:
        db_session (Session): The SQLAlchemy session to interact with the database.
        email (str): The email of the user to retrieve.

    Returns:
        User or None: The user object if found, otherwise None.
    """
    user = await db_session.execute(select(User).filter_by(email=email))
    return user.scalar_one_or_none()


async def authenticate_user(db_session: AsyncSession, email: str, password: str):
    user = await get_user_by_email(db_session, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies if the plain password matches the hashed password.

    Args:
        plain_password (str): The plain text password to verify.
        hashed_password (str): The hashed password to compare against.

    Returns:
        bool: True if the passwords match, otherwise False.
    """
    return PWD_CONTEXT.verify(plain_password, hashed_password)


async def verify_token(token: str):
    try:
        payload = jwt.decode(token, config["SECRET_KEY"], algorithms=config["ALGORITHM"])
        email = payload.get("sub")
        if email is None:
            return None
        return TokenData(email)
    except JWTError:
        return None


async def get_current_user(
    jwt_token: Annotated[str, Depends(OAUTH2_SCHEME)],
    db_session: Annotated[AsyncSession, Depends(async_get_db)],
):
    """
    Retrieve the current user based on the provided JWT token.

    Args:
        token (str): A JWT token extracted from the Authorization header using OAuth2 scheme.
        db_session (Session): The database session for querying the user.

    Returns:
        User: The user object retrieved from the database.

    Raises:
        HTTPException: If the token is invalid, the user email is missing, or the user does not exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(jwt_token, config["SECRET_KEY"], algorithms=config["ALGORITHM"])
        user_email = payload.get("sub")
        if user_email is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="JWT token has expired")
    user = await get_user_by_email(db_session, user_email)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: Annotated[UserSchema, Depends(get_current_user)],
) -> UserSchema:
    """
    Retrieve the current active user, ensuring that the user is active.

    Args:
        current_user (UserSchema): The user object retrieved from the `get_current_user` function.

    Returns:
        UserSchema: The active user object.

    Raises:
        HTTPException: If the user is inactive.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user


async def get_current_user_db(user_id: int, db_session: AsyncSession) -> User:
    """
    Retrieve the current user from the database.

    Args:
        user_id (int): The ID of logged in user.
        db_session (Session): The SQLAlchemy session used to query the database.

    Raises:
        HTTPException: If the user is not found.

    Returns:
        User: The user object retrieved from the database.
    """
    result = await db_session.execute(select(User).filter_by(id=user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


async def handle_refresh_token(refresh_token: str | None, db_session: AsyncSession) -> dict:
    """
    Handles the refresh token process by verifying its validity and generating a new access token.

    Args:
        refresh_token (str | None): The refresh token provided by the client.
        db_session (AsyncSession): The SQLAlchemy session to interact with the database.

    Returns:
        dict: A dictionary containing the new access token and its token type.

    Raises:
        HTTPException: If the refresh token is missing.
        Exception: If the refresh token cannot be verified.
    """
    if not refresh_token:
        raise HTTPException("Refresh token does not exist.")
    user_data = await verify_token(refresh_token, db_session)
    if not user_data:
        raise Exception("Cannot verify the refresh token.")
    new_access_token = await create_access_token(data={"sub": user_data.username_or_email})
    return {"access_token": new_access_token, "token_type": "bearer"}
