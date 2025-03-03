from unittest import mock

import pytest
from fastapi import HTTPException, status

from ..conftest import db_session, test_client
from ..fixtures.constants import (
    GET_RECENTLY_PLAYED_TRACKS_DEFAULT_LIMIT,
    TRACK_DATA_DICT_EXAMPLE,
    USER_SCHEMA_EXAMPLE,
)
from ..fixtures.routers.tracks_router_fixtures import (
    mock_get_current_track,
    mock_get_playback_state,
    mock_get_recently_played_tracks,
    mock_poll_playback_state,
    mock_set_user_polling_status,
    mock_start_polling_tracks,
)

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
@pytest.mark.asyncio
async def test_get_current_track(
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
    response = await test_client.get(f"{PATH}/current")
    assert response.status_code == expected_status
    assert response.json() == expected_response
    mock_get_current_track.assert_awaited_with(1, db_session)


@pytest.mark.parametrize(
    "mock_return_value, mock_side_effect, expected_status_code, expected_response",
    [
        # Test case for success
        (
            {"message": "Playback state polling started in the background."},
            None,
            status.HTTP_200_OK,
            {"message": "Playback state polling started in the background."},
        ),
        # Test case for failure
        (
            None,
            HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "Unauthorized - to start the polling you have to login first.",
            ),
            status.HTTP_401_UNAUTHORIZED,
            {"detail": "Unauthorized - to start the polling you have to login first."},
        ),
    ],
)
@pytest.mark.asyncio
async def test_poll(
    test_client,
    db_session,
    mock_start_polling_tracks,
    mock_return_value,
    mock_side_effect,
    expected_status_code,
    expected_response,
):
    mock_start_polling_tracks.return_value = mock_return_value
    mock_start_polling_tracks.side_effect = mock_side_effect
    response = await test_client.post(f"{PATH}/polling/start")
    assert response.status_code == expected_status_code
    assert response.json() == expected_response
    mock_start_polling_tracks.assert_awaited_once_with(mock.ANY, mock.ANY, db_session)


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
@pytest.mark.asyncio
async def test_get_recently_played_tracks(
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
    response = await test_client.get(f"{PATH}/recently-played")
    assert response.status_code == expected_status
    assert response.json() == expected_response
    mock_get_recently_played_tracks.assert_awaited_with(
        USER_SCHEMA_EXAMPLE.id, db_session, GET_RECENTLY_PLAYED_TRACKS_DEFAULT_LIMIT
    )


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
@pytest.mark.asyncio
async def test_get_playback_state(
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
    response = await test_client.get(f"{PATH}/playback/state")
    assert response.status_code == expected_status
    assert response.json() == expected_response
    mock_get_playback_state.assert_awaited_with(USER_SCHEMA_EXAMPLE.id, db_session)
