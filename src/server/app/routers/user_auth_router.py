from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.db.database import get_db
from app.services.user_auth_service import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    handle_user_register,
)
from app.db.schemas import TokenSchema, UserRegister, UserSchema
from app.services.utils import config

router = APIRouter(tags=["user_auth"], prefix="/user_auth")


@router.post("/register", status_code=201)
async def register_user(user: UserRegister, db_session: Session = Depends(get_db)):
    """
    Handles user registration by calling the `handle_user_register` function. If the registration is successful,
    a new user is created in the database.

    Args:
        user (UserRegister): The user registration data, including email and password.
        db_session (Session, optional): The database session, injected by FastAPI.

    Returns:
        dict: A dictionary containing a success message and the email of the newly registered user.
    """
    return await handle_user_register(db_session, user)


@router.post("/token")
async def generate_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    response: Response,
    db_session: Session = Depends(get_db),
) -> TokenSchema:
    """
    Generate an access token for the user.

    Args:
        form_data (OAuth2PasswordRequestForm): The user's username and password provided in the form.
        response (Response): The response object, used to set the access token as a cookie.
        db_session (Session): The SQLAlchemy session used to interact with the database.

    Raises:
        HTTPException: If the user provides an incorrect username or password, an HTTPException with status 401 is raised.

    Returns:
        TokenSchema: A schema containing the access token and its type ("bearer").
    """
    user = authenticate_user(db_session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=int(config["ACCESS_TOKEN_EXPIRE_MINUTES"]))
    access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        max_age=access_token_expires.total_seconds(),
        samesite="none",
        secure=True,
    )
    return TokenSchema(access_token=access_token, token_type="bearer")


@router.post("/login")
async def login_user(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    response: Response,
    db_session: Session = Depends(get_db),
):
    """
    Log in the user by generating an access token.

    Args:
        form_data (OAuth2PasswordRequestForm): The user's username and password provided in the form.
        response (Response): The response object, used to set the access token as a cookie.
        db_session (Session): The SQLAlchemy session used to interact with the database.

    Returns:
        dict: A dictionary with a message indicating the login was successful.
    """
    await generate_access_token(form_data, response, db_session)
    return {"message": "Login successful"}


@router.get("/users/me/", response_model=UserSchema)
async def read_users_me(
    current_user: Annotated[UserSchema, Depends(get_current_active_user)],
):
    """
    Retrieve the current user's information.

    Args:
        current_user (UserSchema): The currently authenticated user, provided by the dependency `get_current_active_user`.

    Returns:
        UserSchema: A schema containing the user's information.
    """
    return current_user
