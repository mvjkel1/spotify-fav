from sqlalchemy import Boolean, Column, Integer, String

from database import Base


class Track(Base):
    __tablename__ = "tracks"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    spotify_id = Column(Integer, nullable=False)
    listened = Column(Boolean, nullable=False, default=False)
