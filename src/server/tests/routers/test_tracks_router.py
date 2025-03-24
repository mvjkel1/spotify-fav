import httpx
import pytest
from fastapi import HTTPException, status
from ..conftest import db_session, test_client
from ..fixtures.tracks_fixtures import (
    mock_get_current_track,
    mock_is_user_authorized,
    mock_poll_playback_state,
)
from ..fixtures.constants import TRACK_DATA_DICT_EXAMPLE


def test_get_current_track_success(test_client, db_session, mock_get_current_track):
    mock_get_current_track.return_value = TRACK_DATA_DICT_EXAMPLE
    response = test_client.get("/tracks/current-track")
    assert response.status_code == 200
    assert response.json() == TRACK_DATA_DICT_EXAMPLE
    mock_get_current_track.assert_awaited_with(db_session)


def test_get_current_track_failure(test_client, db_session, mock_get_current_track):
    mock_get_current_track.side_effect = HTTPException(status.HTTP_404_NOT_FOUND)
    response = test_client.get("/tracks/current-track")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Not Found"}
    mock_get_current_track.assert_awaited_with(db_session)


def test_poll_success(
    test_client,
    db_session,
    mock_get_current_track,
    mock_is_user_authorized,
    mock_poll_playback_state,
):
    mock_is_user_authorized.return_value = True
    response = test_client.post("/tracks/poll")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Playback state polling started in the background."}
    mock_poll_playback_state.assert_awaited_once_with(db_session)


def test_poll_failure_unauthorized(
    test_client,
    db_session,
    mock_get_current_track,
    mock_is_user_authorized,
    mock_poll_playback_state,
):
    mock_is_user_authorized.return_value = False
    response = test_client.post("/tracks/poll")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": "Unauthorized - to start the polling you have to login first."
    }
