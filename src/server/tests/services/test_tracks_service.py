import httpx
import pytest
from app.db.models import Track, User, user_track_association_table
from app.services.tracks_service import (
    fetch_listened_tracks,
    get_current_track,
    get_playback_state,
    get_recently_played_tracks,
    handle_playing_track,
)
from fastapi import HTTPException, status
from sqlalchemy import insert
from sqlalchemy.ext.asyncio.session import AsyncSession

from ..conftest import db_session
from ..fixtures.constants import (
    GET_CURRENT_TRACK_URL,
    GET_PLAYBACK_STATE_URL,
    GET_RECENTLY_PLAYED_TRACKS_URL,
    SPOTIFY_HEADERS_EXAMPLE,
)
from ..fixtures.services.tracks_service_fixtures import (
    mock_async_client_get,
    mock_config_env,
    mock_extract_track_data,
    mock_get_spotify_headers,
    mock_process_playing_track,
)


@pytest.mark.asyncio
async def test_get_current_track_success(
    db_session, mock_get_spotify_headers, mock_async_client_get, mock_config_env
):
    mock_request = httpx.Request("GET", "mock_request")
    mock_async_client_get.return_value = httpx.Response(
        status_code=status.HTTP_200_OK, json={"track": "track123"}, request=mock_request
    )
    response = await get_current_track(user_id=1, db_session=db_session)
    mock_async_client_get.assert_awaited_with(
        GET_CURRENT_TRACK_URL,
        headers=SPOTIFY_HEADERS_EXAMPLE,
    )
    assert response == {"track": "track123"}


@pytest.mark.asyncio
async def test_get_current_track_failure(
    db_session, mock_get_spotify_headers, mock_async_client_get, mock_config_env
):
    mock_request = httpx.Request("GET", "mock_request")
    mock_async_client_get.return_value = httpx.Response(
        status_code=status.HTTP_401_UNAUTHORIZED, request=mock_request
    )
    with pytest.raises(HTTPException) as exc:
        await get_current_track(user_id=1, db_session=db_session)
    mock_async_client_get.assert_awaited_with(
        GET_CURRENT_TRACK_URL,
        headers=SPOTIFY_HEADERS_EXAMPLE,
    )
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Failed to fetch current track" in exc.value.detail


@pytest.mark.asyncio
async def test_get_recently_played_tracks_success(
    db_session, mock_get_spotify_headers, mock_async_client_get, mock_config_env
):
    mock_request = httpx.Request("GET", "mock_request")
    mock_async_client_get.return_value = httpx.Response(
        status_code=status.HTTP_200_OK,
        json={"track1": "track1", "track2": "track2"},
        request=mock_request,
    )
    response = await get_recently_played_tracks(user_id=1, db_session=db_session)
    mock_async_client_get.assert_awaited_with(
        GET_RECENTLY_PLAYED_TRACKS_URL,
        headers=SPOTIFY_HEADERS_EXAMPLE,
    )
    assert response == {"track1": "track1", "track2": "track2"}


@pytest.mark.asyncio
async def test_get_recently_played_tracks_failure(
    db_session, mock_get_spotify_headers, mock_async_client_get, mock_config_env
):
    mock_request = httpx.Request("GET", "mock_request")
    mock_async_client_get.return_value = httpx.Response(
        status_code=status.HTTP_401_UNAUTHORIZED, request=mock_request
    )
    with pytest.raises(HTTPException) as exc:
        await get_recently_played_tracks(user_id=1, db_session=db_session)
    mock_async_client_get.assert_awaited_with(
        GET_RECENTLY_PLAYED_TRACKS_URL,
        headers=SPOTIFY_HEADERS_EXAMPLE,
    )
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Failed to fetch recently played tracks" in exc.value.detail


@pytest.mark.asyncio
async def test_get_playback_state_success(
    db_session, mock_get_spotify_headers, mock_async_client_get, mock_config_env
):
    mock_request = httpx.Request("GET", "mock_request")
    mock_async_client_get.return_value = httpx.Response(
        status_code=status.HTTP_200_OK, json={"state": "playing"}, request=mock_request
    )
    response = await get_playback_state(user_id=1, db_session=db_session)
    mock_async_client_get.assert_awaited_with(
        GET_PLAYBACK_STATE_URL,
        headers=SPOTIFY_HEADERS_EXAMPLE,
    )
    assert response == {"state": "playing"}


@pytest.mark.asyncio
async def test_get_playback_state_failure(
    db_session, mock_get_spotify_headers, mock_async_client_get, mock_config_env
):
    mock_request = httpx.Request("GET", "mock_request")
    mock_async_client_get.return_value = httpx.Response(
        status_code=status.HTTP_401_UNAUTHORIZED, request=mock_request
    )
    with pytest.raises(HTTPException) as exc:
        await get_playback_state(user_id=1, db_session=db_session)
    mock_async_client_get.assert_awaited_with(
        GET_PLAYBACK_STATE_URL,
        headers=SPOTIFY_HEADERS_EXAMPLE,
    )
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Failed to fetch playback state" in exc.value.detail


@pytest.mark.parametrize(
    "expected_args",
    [
        {
            "track_db": None,
            "ten_seconds_passed": True,
            "ten_seconds_left": False,
            "track_title": "test track",
            "id": "test_track_id",
            "user_id": 1,
        }
    ],
)
@pytest.mark.asyncio
async def test_handle_playing_track_success(db_session, mock_process_playing_track, expected_args):
    state = {
        "is_playing": True,
        "progress_ms": 10000,
        "item": {
            "duration_ms": 11112222,
            "name": "test track",
            "id": "test_track_id",
        },
    }

    await handle_playing_track(state, user_id=1, db_session=db_session)
    mock_process_playing_track.assert_awaited_with(*expected_args.values(), db_session)


@pytest.mark.asyncio
async def test_handle_playing_track_failure(
    db_session,
    mock_process_playing_track,
):
    state = {
        "is_playing": False,
        "progress_ms": 10000,
        "item": {"duration_ms": 11112222, "name": "test track", "id": "test_track_id"},
    }
    await handle_playing_track(state, user_id=1, db_session=db_session)
    mock_process_playing_track.assert_not_awaited()


@pytest.mark.asyncio
async def test_fetch_listened_tracks_success(db_session: AsyncSession):
    test_user = User(id=1, spotify_uid=1, email="user@example.com", hashed_password="P!w!D")
    db_session.add(test_user)
    test_track = Track(
        id=1,
        title="Test Track",
        spotify_id="test_id",
    )
    db_session.add(test_track)
    await db_session.execute(
        insert(user_track_association_table).values(
            user_id=test_user.id, track_id=test_track.id, listened_count=1
        )
    )
    await db_session.commit()

    response = await fetch_listened_tracks(user_id=1, db_session=db_session)
    assert len(response) == 1
    fetched_track = response[0]
    assert isinstance(fetched_track, Track)
    assert fetched_track.title == test_track.title
    assert fetched_track.spotify_id == test_track.spotify_id


@pytest.mark.asyncio
async def test_fetch_listened_tracks_failure(db_session):
    test_track = Track(title="Test Track", spotify_id="test_id")
    db_session.add(test_track)
    await db_session.commit()
    with pytest.raises(HTTPException) as exc:
        await fetch_listened_tracks(user_id=1, db_session=db_session)
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "No tracks you have listened to were found."
