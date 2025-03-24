from pydantic import BaseModel


class TokenRequest(BaseModel):
    client_id: str
    client_secret: str


class PlaybackStateResponse(BaseModel):
    is_playing: bool
    progress_ms: int
    item: dict
