import httpx
import pytest
from fastapi import HTTPException, status
from ..conftest import db_session, test_client
from ..fixtures.tracks_fixtures import (
    mock_get_current_track,
    mock_is_user_authorized,
    mock_poll_playback_state,
    mock_get_playback_state,
    mock_get_recently_played_tracks,
)
from ..fixtures.constants import TRACK_DATA_DICT_EXAMPLE

PATH = "/tracks"


@pytest.mark.parametrize(
    "mock_return_value, mock_side_effect, expected_status, expected_response",
    [
        (TRACK_DATA_DICT_EXAMPLE, None, 200, TRACK_DATA_DICT_EXAMPLE),
        (
            None,
            HTTPException(status.HTTP_404_NOT_FOUND),
            status.HTTP_404_NOT_FOUND,
            {"detail": "Not Found"},
        ),
    ],
)
def test_get_current_track(
    test_client,
    db_session,
    mock_get_current_track,
    mock_return_value,
    mock_side_effect,
    expected_status,
    expected_response,
):
    mock_get_current_track.return_value = mock_return_value
    mock_get_current_track.side_effect = mock_side_effect
    response = test_client.get(f"{PATH}/current-track")
    assert response.status_code == expected_status
    assert response.json() == expected_response
    mock_get_current_track.assert_awaited_with(db_session)


@pytest.mark.parametrize(
    "is_authorized, expected_status, expected_response",
    [
        (
            True,
            status.HTTP_200_OK,
            {"message": "Playback state polling started in the background."},
        ),
        (
            False,
            status.HTTP_401_UNAUTHORIZED,
            {"detail": "Unauthorized - to start the polling you have to login first."},
        ),
    ],
)
def test_poll(
    test_client,
    db_session,
    mock_is_user_authorized,
    mock_poll_playback_state,
    is_authorized,
    expected_status,
    expected_response,
):
    mock_is_user_authorized.return_value = is_authorized
    response = test_client.post(f"{PATH}/poll")
    assert response.status_code == expected_status
    assert response.json() == expected_response
    if is_authorized:
        mock_poll_playback_state.assert_awaited_once_with(db_session)


@pytest.mark.parametrize(
    "mock_return_value, mock_side_effect, expected_status, expected_response",
    [
        (
            {"tracks": "track1", "tracks": "track2"},
            None,
            status.HTTP_200_OK,
            {"tracks": "track1", "tracks": "track2"},
        ),
        (
            None,
            HTTPException(status.HTTP_404_NOT_FOUND),
            status.HTTP_404_NOT_FOUND,
            {"detail": "Not Found"},
        ),
    ],
)
def test_get_recently_played(
    test_client,
    db_session,
    mock_get_recently_played_tracks,
    mock_return_value,
    mock_side_effect,
    expected_status,
    expected_response,
):
    mock_get_recently_played_tracks.return_value = mock_return_value
    mock_get_recently_played_tracks.side_effect = mock_side_effect
    response = test_client.get(f"{PATH}/recently-played")
    assert response.status_code == expected_status
    assert response.json() == expected_response
    mock_get_recently_played_tracks.assert_awaited_with(db_session, 1)


@pytest.mark.parametrize(
    "mock_return_value, mock_side_effect, expected_status, expected_response",
    [
        ({"state": "playing"}, None, status.HTTP_200_OK, {"state": "playing"}),
        (
            None,
            HTTPException(status.HTTP_404_NOT_FOUND),
            status.HTTP_404_NOT_FOUND,
            {"detail": "Not Found"},
        ),
    ],
)
def test_get_playback_state(
    test_client,
    db_session,
    mock_get_playback_state,
    mock_return_value,
    mock_side_effect,
    expected_status,
    expected_response,
):
    mock_get_playback_state.return_value = mock_return_value
    mock_get_playback_state.side_effect = mock_side_effect
    response = test_client.get(f"{PATH}/playback-state")
    assert response.status_code == expected_status
    assert response.json() == expected_response
    mock_get_playback_state.assert_awaited_with(db_session)
