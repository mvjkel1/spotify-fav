SPOTIFY_HEADERS_EXAMPLE = {
    "Authorization": "Bearer access_token",
    "Content-Type": "application/json",
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


def get_model_attributes(instance):
    return {
        key: value
        for key, value in instance.__dict__.items()
        if not key.startswith("_")
    }
