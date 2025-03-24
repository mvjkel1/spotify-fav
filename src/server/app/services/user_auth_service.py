from typing import Annotated
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.models import User
from passlib.context import CryptContext
from fastapi import status
from app.db.schemas import UserRegister
from datetime import datetime, timezone, timedelta
from app.services.utils import config
from jose import jwt
from jwt.exceptions import InvalidTokenError

from app.db.database import get_db
from app.db.schemas import UserSchema

OAUTH2_SCHEME = OAuth2PasswordBearer(tokenUrl="/user_auth/token")
PWD_CONTEXT = CryptContext(schemes=["argon2"], deprecated="auto")


async def handle_user_register(
    db_session: Session,
    user: UserRegister,
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
    existing_user = get_user_by_email(db_session, user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )
    hashed_password = hash_password(user.password)
    new_user = User(email=user.email, hashed_password=hashed_password)
    db_session.add(new_user)
    db_session.commit()
    db_session.refresh(new_user)
    return {"message": "User registered successfully", "email": new_user.email}


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Creates an access token with an expiration time. The token is encoded using a secret key.

    Args:
        data (dict): The data to include in the token payload.
        expires_delta (timedelta, optional): The expiration time of the token. Default is 15 minutes.

    Returns:
        str: The encoded JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config["SECRET_KEY"], algorithm=config["ALGORITHM"])
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


def get_user_by_email(db_session: Session, email: str) -> User | None:
    """
    Retrieves a user from the database by their email address.

    Args:
        db_session (Session): The SQLAlchemy session to interact with the database.
        email (str): The email of the user to retrieve.

    Returns:
        User or None: The user object if found, otherwise None.
    """
    return db_session.query(User).filter_by(email=email).first()


def authenticate_user(db_session: Session, email: str, password: str):
    user = get_user_by_email(db_session, email)
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


def get_current_user(
    jwt_token: Annotated[str, Depends(OAUTH2_SCHEME)],
    db_session: Annotated[Session, Depends(get_db)],
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
    user = get_user_by_email(db_session, user_email)
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


def get_current_user_db(user_id: int, db_session: Session) -> User:
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
    user = db_session.query(User).filter_by(id=user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
