from datetime import datetime
from typing import List

from pydantic import BaseModel


class TrackBase(BaseModel):
    id: int
    spotify_id: str
    title: str
    listened_count: int
    added_at: datetime


class TrackResponse(TrackBase):
    class Config:
        from_attributes = True


class PlaylistBase(BaseModel):
    id: int
    spotify_id: str
    name: str
    created_at: datetime


class PlaylistResponse(PlaylistBase):
    tracks: List[TrackResponse]

    class Config:
        from_attributes = True
