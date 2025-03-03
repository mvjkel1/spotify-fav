from pydantic import BaseModel

from database import Base


class TokenRequest(BaseModel):
    client_id: str
    client_secret: str


# TODO
class Track(Base):
    pass
