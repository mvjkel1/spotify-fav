from app.db.models import Track, User

SPOTIFY_HEADERS_EXAMPLE = {
    "Authorization": "Bearer access_token",
    "Content-Type": "application/json",
}

ENV_CONFIG_EXAMPLE = {
    "CLIENT_ID": "CLIENT_ID",
    "CLIENT_SECRET": "CLIENT_SECRET",
    "SPOTIFY_API_SCOPES": "SPOTIFY_API_SCOPES",
    "SPOTIFY_API_URL": "SPOTIFY_API_URL",
    "SPOTIFY_TOKEN_URL": "SPOTIFY_TOKEN_URL",
    "REDIRECT_URI": "REDIRECT_URI",
    "CALLBACK_REDIRECT_URL": "CALLBACK_REDIRECT_URL",
    "SPOTIFY_AUTH_URL": "SPOTIFY_AUTH_URL",
    "REDIS_URL": "REDIS_URL",
    "REDIS_TOKEN": "REDIS_TOKEN",
    "SECRET_KEY": "!SECRET_KEY!",
    "REFRESH_TOKEN_EXPIRE_DAYS": 4,
    "ACCESS_TOKEN_EXPIRE_MINUTES": 20,
    "ALGORITHM": "HS256",
}

USER_DATA_EXAMPLE = {
    "id": "user123",
    "display_name": "Test User",
    "email": "testuser@example.com",
}

USER_DATA_EXAMPLE_MALFORMED = {
    "XiXdX": "user123",
    "display_name": "Test User",
    "email": "testuser@example.com",
}

ACCESS_TOKEN_EXAMPLE = {
    "access_token": "fake_access_token",
    "refresh_token": "fake_refresh_token",
    "expires_in": 3600,
}

TRACK_DATA_EXAMPLE = (10000, 12000, "Test track", "test_track_id")

TRACK_DATA_DICT_EXAMPLE = {
    "track_id": "123",
    "name": "Test Track",
    "artist": "Test Artist",
    "album": "Test Album",
}

GET_CURRENT_USER_URL = f"{ENV_CONFIG_EXAMPLE["SPOTIFY_API_URL"]}/me"

GET_CURRENT_TRACK_URL = f"{ENV_CONFIG_EXAMPLE["SPOTIFY_API_URL"]}/me/player/currently-playing"

GET_RECENTLY_PLAYED_TRACKS_URL = (
    f"{ENV_CONFIG_EXAMPLE["SPOTIFY_API_URL"]}/me/player/recently-played?limit=1"
)

GET_PLAYBACK_STATE_URL = f"{ENV_CONFIG_EXAMPLE["SPOTIFY_API_URL"]}/me/player"

GET_MY_PLAYLISTS_URL_EXAMPLE = (
    f"{ENV_CONFIG_EXAMPLE["SPOTIFY_API_URL"]}/users/1/playlists?offset=0&limit=10"
)

CREATE_PLAYLIST_SERVICE_URL_EXAMPLE = f"{ENV_CONFIG_EXAMPLE["SPOTIFY_API_URL"]}/playlists/10/tracks"

USER_ID_EXAMPLE = "123"

SPOTIFY_USER_ID_EXAMPLE = "114477"

EXAMPLE_TRACK_ID = "25"

TRACK_EXAMPLE_DB = Track(
    id=EXAMPLE_TRACK_ID,
    title="Test Track",
    spotify_id="test_id",
)

USER_EXAMPLE_DB = User(id=1, spotify_uid=1, email="user@example.com", hashed_password="P!w!D")
