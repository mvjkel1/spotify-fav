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
GET_CURRENT_TRACK_URL = f"{ENV_CONFIG_EXAMPLE["SPOTIFY_API_URL"]}/me/player/currently-playing"
GET_RECENTLY_PLAYED_TRACKS_URL = (
    f"{ENV_CONFIG_EXAMPLE["SPOTIFY_API_URL"]}/me/player/recently-played?limit=1"
)
GET_PLAYBACK_STATE_URL = f"{ENV_CONFIG_EXAMPLE["SPOTIFY_API_URL"]}/me/player"
GET_MY_PLAYLISTS_URL = (
    f"{ENV_CONFIG_EXAMPLE["SPOTIFY_API_URL"]}/users/1/playlists?offset=0&limit=10"
)
CREATE_PLAYLIST_SERVICE_URL = f"{ENV_CONFIG_EXAMPLE["SPOTIFY_API_URL"]}/playlists/10/tracks"
