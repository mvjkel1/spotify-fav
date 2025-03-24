from sqlalchemy import Column, Float, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship

from app.db.database import Base

playlist_track_association_table = Table(
    "playlist_track",
    Base.metadata,
    Column("playlist_id", Integer, ForeignKey("playlists.id")),
    Column("track_id", Integer, ForeignKey("tracks.id")),
)


class Track(Base):
    """
    Represents a music track in the API.

    Attributes:
        id (int): The unique identifier for the track.
        spotify_id (str): The Spotify ID for the track.
        title (str): The title of the track.
        listened_count (int): The number of times the track has been listened to.
        playlists (relationship): A many-to-many relationship with the Playlist model.
    """

    __tablename__ = "tracks"
    id = Column(Integer, primary_key=True)
    spotify_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    listened_count = Column(Integer, default=0)
    playlists = relationship(
        "Playlist", secondary=playlist_track_association_table, back_populates="tracks"
    )


class Playlist(Base):
    """
    Represents a playlist in the API.

    Attributes:
        id (int): The unique identifier for the playlist.
        name (str): The name of the playlist.
        tracks (relationship): A many-to-many relationship with the Track model.
    """

    __tablename__ = "playlists"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    tracks = relationship(
        "Track", secondary=playlist_track_association_table, back_populates="playlists"
    )


class AccessToken(Base):
    __tablename__ = "tokens"
    id = Column(Integer, primary_key=True)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=False)
    expires_at = Column(Float, nullable=True)
