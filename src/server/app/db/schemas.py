from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TrackBase(BaseModel):
    id: int
    spotify_id: str
    title: str
    listened_count: int
    added_at: datetime


class TrackResponse(TrackBase):
    model_config = ConfigDict(from_attributes=True)


class PlaylistBase(BaseModel):
    id: int
    spotify_id: str
    name: str
    created_at: datetime


class PlaylistResponse(PlaylistBase):
    tracks: List[TrackResponse]
    model_config = ConfigDict(from_attributes=True)


class UserSchema(BaseModel):
    id: int
    email: str
    is_polling: bool


class TokenSchema(BaseModel):
    access_token: str
    token_type: str


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=32)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenData(BaseModel):
    email: EmailStr
