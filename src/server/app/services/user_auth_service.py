from datetime import datetime, timedelta, timezone
from typing import Annotated

from app.db.database import async_get_db
from app.db.models import User
from app.db.schemas import TokenSchema, UserRegister, UserSchema
from app.services.utils import config
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

OAUTH2_SCHEME = OAuth2PasswordBearer(tokenUrl="user-auth/token")
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
        HTTPException: User with given email address is already registered.

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


async def authenticate_user(db_session: AsyncSession, email: str, password: str) -> User | bool:
    """
    Authenticate a user based on the provided email and password.

    Args:
        db_session (AsyncSession): The SQLAlchemy session used to interact with the database.
        email (str): The email address of the user.
        password (str): The password provided by the user.

    Returns:
        User | bool: User object if the authentication is successful, otherwise False.
    """
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


async def get_current_user(
    jwt_token: Annotated[str, Depends(OAUTH2_SCHEME)],
    db_session: Annotated[AsyncSession, Depends(async_get_db)],
) -> User:
    """
    Retrieve the current user based on the provided JWT token.

    Args:
        jwt_token (str): A JWT token extracted from the Authorization header using OAuth2 scheme.
        db_session (Session): The database session for querying the user.

    Returns:
        User: The user object retrieved from the database.

    Raises:
        HTTPException: If the token is invalid, the user email is missing, or the user does not exist.
    """
    user_email = decode_jwt_token(jwt_token, config["SECRET_KEY"], config["ALGORITHM"])
    user = await get_user_by_email(db_session, user_email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def decode_jwt_token(token: str, secret_key: str, algorithm: str) -> str:
    """
    Decode a JWT token and extract the user email from the 'sub' claim.

    Args:
        token (str): The JWT token to decode.
        secret_key (str): The secret key used to verify the token signature.
        algorithm (str): The algorithm used for decoding the token.

    Returns:
        str: The user email extracted from the token's 'sub' claim.

    Raises:
        HTTPException: The token is invalid, expired, or missing required claims.
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        user_email = payload.get("sub")
        if not user_email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload missing 'sub' claim",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_email


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
        db_session (AsyncSession): The SQLAlchemy async session used to query the database.

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


async def refresh_access_token(
    request: Request, response: Response, db_session: AsyncSession
) -> TokenSchema:
    """
    Refreshes the access token using the provided refresh token.

    Args:
        request (Request): The request object containing the refresh token.
        response (Response): The response object to set the access token.
        db_session (AsyncSession): The SQLAlchemy session used to query the database.

    Returns:
        TokenSchema: Access token created using the refresh token.
    """
    refresh_token = request.cookies.get("refresh_token", None)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Refresh token does not exist."
        )
    user_email = decode_jwt_token(refresh_token, config["SECRET_KEY"], config["ALGORITHM"])
    user = await get_user_by_email(db_session, user_email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    access_token_expires = timedelta(minutes=int(config["ACCESS_TOKEN_EXPIRE_MINUTES"]))
    new_access_token = create_access_token(data={"sub": user.email})
    set_cookie(
        response,
        "access_token",
        f"Bearer {new_access_token}",
        access_token_expires,
    )
    return TokenSchema(access_token=new_access_token, token_type="Bearer")


async def generate_tokens(
    form_data: OAuth2PasswordRequestForm, response: Response, db_session: AsyncSession
):
    """
    Generates access and refresh tokens for the user and sets them as cookies in the response.

    Args:
        form_data (OAuth2PasswordRequestForm): The form data containing the user's username and password.
        response (Response): The response object to set the tokens as cookies.
        db_session (AsyncSession): The SQLAlchemy session used to interact with the database.
    """
    user = await authenticate_user_from_form(form_data, db_session)
    access_token, refresh_token = create_tokens_for_user(user)
    set_token_cookies(response, access_token, refresh_token)
    return access_token, refresh_token


async def authenticate_user_from_form(
    form_data: OAuth2PasswordRequestForm, db_session: AsyncSession
) -> User | bool:
    """
    Authenticate the user based on the provided username and password.

    Args:
        form_data (OAuth2PasswordRequestForm): The form data containing the user's username and password.
        db_session (AsyncSession): The SQLAlchemy session used to interact with the database.

    Returns:
        User | bool: User object if the authentication is successful, otherwise False.
    """
    user = await authenticate_user(db_session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def create_tokens_for_user(user: User) -> tuple[str, str]:
    """
    Creates both access and refresh tokens for the given user.

    Args:
        user (User): The user object for which the tokens are being created.

    Returns:
        tuple[str, str]access_token (str): A tuple containing generated access and refresh tokens.
    """
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    return access_token, refresh_token


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


def set_token_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """
    Set the access and refresh tokens as cookies in the response.

    Args:
        response (Response): The response object to set the tokens as cookies.
        access_token (str): The access token to be set in the cookies.
        refresh_token (str): The refresh token to be set in the cookies.
    """
    set_cookie(
        response,
        "access_token",
        f"Bearer {access_token}",
        timedelta(minutes=int(config["ACCESS_TOKEN_EXPIRE_MINUTES"])),
    )
    set_cookie(
        response,
        "refresh_token",
        refresh_token,
        timedelta(days=int(config["REFRESH_TOKEN_EXPIRE_DAYS"])),
    )


def set_cookie(response: Response, key: str, value: str, expires: timedelta) -> None:
    """
    Sets a secure HTTP-only cookie on the given response object.

    Args:
        response (Response): The HTTP response object to which the cookie will be added.
        key (str): The name of the cookie.
        value (str): The value to store in the cookie.
        expires (timedelta): The duration until the cookie expires.
    """
    response.set_cookie(
        key=key,
        value=value,
        max_age=expires.total_seconds(),
        expires=(datetime.now(tz=timezone.utc) + expires),
        httponly=True,
        secure=True,
        samesite="Lax",
    )
