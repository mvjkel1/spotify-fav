import pytest
from fastapi import HTTPException, status

from ..conftest import db_session, test_client
from ..fixtures.routers.playlists_router_fixtures import (
    mock_get_playlists_from_spotify,
    mock_process_playlist_creation,
)

PATH = "/playlists"


@pytest.mark.parametrize(
    ("mock_return_value", "mock_side_effect", "expected_status", "expected_response"),
    [
        (
            {"playlists": ["playlist1", "playlist2", "playlist3"]},
            None,
            status.HTTP_200_OK,
            {"playlists": ["playlist1", "playlist2", "playlist3"]},
        ),
        (
            None,
            HTTPException(status.HTTP_404_NOT_FOUND),
            status.HTTP_404_NOT_FOUND,
            {"detail": "Not Found"},
        ),
    ],
)
def test_get_my_playlists(
    db_session,
    test_client,
    mock_get_playlists_from_spotify,
    mock_return_value,
    mock_side_effect,
    expected_status,
    expected_response,
):
    mock_get_playlists_from_spotify.return_value = mock_return_value
    mock_get_playlists_from_spotify.side_effect = mock_side_effect
    response = test_client.get(f"{PATH}/")
    assert response.status_code == expected_status
    assert response.json() == expected_response
    mock_get_playlists_from_spotify.assert_awaited_with(0, 20, db_session)


@pytest.mark.parametrize(
    (
        "mock_return_value",
        "mock_side_effect",
        "playlist_name",
        "expected_status",
        "expected_response",
    ),
    [
        (
            {"message": "Playlist created sucessfully"},
            None,
            "Test Playlist",
            status.HTTP_200_OK,
            {"message": "Playlist created sucessfully"},
        ),
        (
            None,
            HTTPException(status.HTTP_404_NOT_FOUND),
            "Test Playlist",
            status.HTTP_404_NOT_FOUND,
            {"detail": "Not Found"},
        ),
    ],
)
def test_create_playlist(
    db_session,
    test_client,
    mock_process_playlist_creation,
    mock_return_value,
    mock_side_effect,
    playlist_name,
    expected_status,
    expected_response,
):
    mock_process_playlist_creation.return_value = mock_return_value
    mock_process_playlist_creation.side_effect = mock_side_effect
    response = test_client.post(f"{PATH}/create?playlist_name={playlist_name}")
    assert response.json() == expected_response
    assert response.status_code == expected_status
    mock_process_playlist_creation.assert_awaited_with(playlist_name, db_session)
