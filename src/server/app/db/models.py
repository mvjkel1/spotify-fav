from datetime import datetime, timezone

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base

playlist_track_association_table = Table(
    "playlist_track",
    Base.metadata,
    Column("playlist_id", Integer, ForeignKey("playlists.id", ondelete="CASCADE")),
    Column("track_id", Integer, ForeignKey("tracks.id", ondelete="CASCADE")),
)

user_playlist_association_table = Table(
    "user_playlist",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE")),
    Column("playlist_id", Integer, ForeignKey("playlists.id", ondelete="CASCADE")),
    UniqueConstraint("user_id", "playlist_id", name="uq_user_playlist"),
)

user_track_association_table = Table(
    "user_track",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("track_id", Integer, ForeignKey("tracks.id", ondelete="CASCADE"), primary_key=True),
    Column("listened_count", Integer, default=0, nullable=False),
    UniqueConstraint("user_id", "track_id", name="uq_user_track"),
)


class User(Base):
    """
    Represents a user in the system.

    Attributes:
        id (int): The primary key for the user.
        email (str): The unique email of the user.
        hashed_password (str): The password hash of the user.
        is_polling (bool): Indicates whether the user is actively polling data. Default is False.
        last_login (datetime): The timestamp of the user's last login. Optional.
        playlists (list): A one-to-many relationship linking users and playlists.
        spotify_access_token (SpotifyAccessToken): A one-to-one relationship linking the user to their Spotify access token.
    """

    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    spotify_uid = Column(String, unique=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_polling = Column(Boolean, default=False, nullable=True)
    is_active = Column(Boolean, default=True)
    last_login = Column(type_=TIMESTAMP(timezone=True), default=None, nullable=True)
    tracks = relationship("Track", secondary=user_track_association_table, back_populates="users")
    playlists = relationship("Playlist", back_populates="user", cascade="all, delete")
    spotify_access_token = relationship(
        "SpotifyAccessToken", back_populates="user", uselist=False, cascade="all, delete"
    )


class SpotifyAccessToken(Base):
    """
    Represents an access token for Spotify's API, used by the user for authentication.

    Attributes:
        id (int): The primary key for the access token.
        access_token (str): The token used to authenticate requests to Spotify's API.
        refresh_token (str): The token used to refresh the access token.
        expires_at (datetime): The timestamp when the access token expires.
        created_at (datetime): The timestamp when the token was created.
        updated_at (datetime): The timestamp when the token was last updated.
        user_id (int): The foreign key linking the token to a user.
        user (User): The relationship linking the token to the associated user.
    """

    __tablename__ = "spotify_access_tokens"
    id = Column(Integer, primary_key=True)
    access_token = Column(String, unique=True, nullable=False)
    refresh_token = Column(String, unique=True, nullable=False)
    created_at = Column(
        type_=TIMESTAMP(timezone=True), default=datetime.now(tz=timezone.utc), nullable=False
    )
    expires_at = Column(Float, nullable=False)
    updated_at = Column(
        type_=TIMESTAMP(timezone=True),
        onupdate=datetime.now(tz=timezone.utc),
    )
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user = relationship("User", back_populates="spotify_access_token")

    def is_expired(self):
        """
        Checks if the access token has expired.

        Returns:
            bool: True if the access token has expired, otherwise False.
        """
        return datetime.now(tz=timezone.utc).timestamp() >= self.expires_at


class Track(Base):
    """
    Represents a music track in the database.

    Attributes:
        id (int): The unique identifier for the track.
        spotify_id (str): The unique Spotify ID for the track.
        title (str): The title of the track.
        listened_count (int): The number of times the track has been listened to.
        added_at (datetime): The timestamp when the track was added to the database.
        playlists (relationship): A many-to-many relationship linking tracks and playlists.
    """

    __tablename__ = "tracks"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    spotify_id = Column(String, nullable=False)
    users = relationship("User", secondary=user_track_association_table, back_populates="tracks")
    playlists = relationship(
        "Playlist", secondary=playlist_track_association_table, back_populates="tracks"
    )


class Playlist(Base):
    """
    Represents a playlist in the DB.

    Attributes:
        id (int): The unique identifier for the playlist.
        name (str): The name of the playlist.
        user_id (int): The foreign key linking the playlist to a user.
        user (User): The relationship linking the playlist to the associated user.
        tracks (list): A many-to-many relationship with the Track model.
    """

    __tablename__ = "playlists"
    id = Column(Integer, primary_key=True)
    spotify_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user = relationship("User", back_populates="playlists")
    tracks = relationship(
        "Track", secondary=playlist_track_association_table, back_populates="playlists"
    )
    created_at = Column(type_=TIMESTAMP(timezone=True), default=datetime.now(tz=timezone.utc))
