import httpx
import pytest
from app.db.models import Playlist
from app.services.playlists_service import (
    cache_playlist_tracks,
    get_playlists_from_spotify,
    process_playlist_creation,
    retrieve_playlist_from_spotify_by_spotify_id,
    sync_playlists,
)
from fastapi import HTTPException, status
from sqlalchemy import select

from ..fixtures.constants import (
    GET_MY_PLAYLISTS_URL_EXAMPLE,
    SPOTIFY_HEADERS_EXAMPLE,
    SPOTIFY_PLAYLIST_ID_EXAMPLE,
    SPOTIFY_USER_ID_EXAMPLE,
    TRACK_EXAMPLE_DB,
    TRACKS_LIST_EXAMPLE,
    USER_ID_EXAMPLE,
)
from ..fixtures.services.playlists_service_fixtures import (
    mock_async_client_get,
    mock_async_client_post,
    mock_config_env,
    mock_create_playlist,
    mock_create_playlist_on_spotify,
    mock_fetch_listened_tracks,
    mock_filter_new_tracks,
    mock_get_all_playlists,
    mock_get_current_spotify_user_id,
    mock_get_current_user_db,
    mock_get_spotify_headers,
    mock_redis,
    mock_sync_playlists,
)
from ..utils.utils import add_test_user, add_test_user_and_track


@pytest.mark.asyncio
async def test_get_playlists_from_spotify_success(
    db_session,
    mock_get_spotify_headers,
    mock_async_client_get,
    mock_get_current_user_db,
):
    mock_request = httpx.Request("GET", "mock_request")
    mock_async_client_get.return_value = httpx.Response(
        status_code=status.HTTP_200_OK,
        json={"playlist1": "playlist1", "playlist2": "playlist2"},
        request=mock_request,
    )
    response = await get_playlists_from_spotify(
        offset=0, limit=10, user_id=USER_ID_EXAMPLE, db_session=db_session
    )
    assert response == {"playlist1": "playlist1", "playlist2": "playlist2"}
    mock_async_client_get.assert_awaited_with(
        GET_MY_PLAYLISTS_URL_EXAMPLE, headers=SPOTIFY_HEADERS_EXAMPLE
    )
    mock_get_spotify_headers.assert_called_once_with(USER_ID_EXAMPLE, db_session)


@pytest.mark.asyncio
async def test_retrieve_playlist_from_spotify_by_spotify_id_success(
    db_session, mock_get_spotify_headers, mock_async_client_get
):
    mock_request = httpx.Request("GET", "mock_request")
    mock_async_client_get.return_value = httpx.Response(
        status_code=status.HTTP_200_OK,
        json={"playlist1": "data"},
        request=mock_request,
    )
    response = await retrieve_playlist_from_spotify_by_spotify_id(
        spotify_id=SPOTIFY_PLAYLIST_ID_EXAMPLE, user_id=USER_ID_EXAMPLE, db_session=db_session
    )
    assert response == {"playlist1": "data"}
    mock_get_spotify_headers.assert_called_once_with(USER_ID_EXAMPLE, db_session)


@pytest.mark.asyncio
async def test_retrieve_playlist_from_spotify_by_spotify_id_success(
    db_session, mock_get_spotify_headers, mock_async_client_get
):
    mock_request = httpx.Request("GET", "mock_request")
    mock_async_client_get.return_value = httpx.Response(
        status_code=status.HTTP_200_OK,
        json={"playlist1": "data"},
        request=mock_request,
    )
    response = await retrieve_playlist_from_spotify_by_spotify_id(
        spotify_id=SPOTIFY_PLAYLIST_ID_EXAMPLE, user_id=USER_ID_EXAMPLE, db_session=db_session
    )
    assert response == {"playlist1": "data"}
    mock_get_spotify_headers.assert_called_once_with(USER_ID_EXAMPLE, db_session)


@pytest.mark.asyncio
async def test_retrieve_playlist_from_spotify_by_spotify_id_unauthorized(
    db_session, mock_get_spotify_headers, mock_async_client_get
):
    mock_request = httpx.Request("GET", "mock_request")
    mock_async_client_get.return_value = httpx.Response(
        status_code=status.HTTP_401_UNAUTHORIZED,
        json={"error": "Unauthorized"},
        request=mock_request,
    )
    response = await retrieve_playlist_from_spotify_by_spotify_id(
        spotify_id=SPOTIFY_PLAYLIST_ID_EXAMPLE, user_id=USER_ID_EXAMPLE, db_session=db_session
    )
    assert response == {"error": "Unauthorized"}
    mock_get_spotify_headers.assert_called_once_with(USER_ID_EXAMPLE, db_session)


@pytest.mark.asyncio
async def test_sync_playlists(db_session, mock_get_all_playlists):
    mock_db_playlists = [
        Playlist(
            name=f"spotify_fav_{genre}",
            spotify_id=f"playlist_id_{i}",
            tracks=TRACKS_LIST_EXAMPLE,
            user_id=USER_ID_EXAMPLE,
        )
        for i, genre in enumerate(["rock", "pop", "jazz"], start=1)
    ]
    db_session.add_all(mock_db_playlists)
    await db_session.commit()
    mock_get_all_playlists.return_value = {
        "items": [
            {"id": "playlist_id_1", "name": "spotify_fav_rock"},
            {"id": "playlist_id_3", "name": "spotify_fav_pop"},
            {"id": "playlist_id_4", "name": "spotify_fav_jazz"},
        ]
    }
    await sync_playlists(user_id=USER_ID_EXAMPLE, db_session=db_session)
    result = await db_session.execute(select(Playlist))
    db_playlists = result.scalars().all()
    # Playlists in DB: {"playlist_1", "playlist_2", "playlist_3"}
    # Playlists in Spotify: {"playlist_1", "playlist_3", "playlist_4"}
    # Playlist to remove: {"playlist_2"} (present in DB but not in Spotify)
    # Verify "playlist_id_2" was removed
    assert len(db_playlists) == 2
    assert "playlist_id_2" not in [playlist.id for playlist in db_playlists]


@pytest.mark.asyncio
async def test_process_playlist_creation_success(
    db_session,
    mock_get_spotify_headers,
    mock_get_current_user_db,
    mock_create_playlist,
    mock_filter_new_tracks,
    mock_get_current_spotify_user_id,
    mock_get_all_playlists,
    mock_sync_playlists,
):
    mock_filter_new_tracks.return_value = [TRACK_EXAMPLE_DB]
    await add_test_user_and_track(db_session)
    response = await process_playlist_creation("test", USER_ID_EXAMPLE, db_session)
    mock_create_playlist.assert_awaited_once_with(
        "test",
        mock_filter_new_tracks.return_value,
        SPOTIFY_USER_ID_EXAMPLE,
        USER_ID_EXAMPLE,
        db_session,
        SPOTIFY_HEADERS_EXAMPLE,
    )
    assert response == {"message": "The 'test' playlist was created successfully."}


@pytest.mark.asyncio
async def test_get_playlists_from_spotify_failure(
    db_session,
    mock_get_spotify_headers,
    mock_async_client_get,
    mock_get_current_user_db,
):
    mock_request = httpx.Request("GET", "mock_request")
    mock_async_client_get.return_value = httpx.Response(
        status_code=status.HTTP_404_NOT_FOUND,
        json={"ERROR": "ERROR"},
        request=mock_request,
    )
    with pytest.raises(HTTPException) as exc:
        await get_playlists_from_spotify(
            offset=0, limit=10, user_id=USER_ID_EXAMPLE, db_session=db_session
        )
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Failed to retrieve spotify playlists."
    mock_async_client_get.assert_awaited_with(
        GET_MY_PLAYLISTS_URL_EXAMPLE, headers=SPOTIFY_HEADERS_EXAMPLE
    )
    mock_get_spotify_headers.assert_called_once_with(USER_ID_EXAMPLE, db_session)


@pytest.mark.asyncio
async def test_process_playlist_creation_failure(
    db_session,
    mock_get_spotify_headers,
    mock_get_current_user_db,
    mock_get_current_spotify_user_id,
    mock_get_all_playlists,
    mock_create_playlist,
    mock_create_playlist_on_spotify,
    mock_sync_playlists,
):
    await add_test_user(db_session)
    with pytest.raises(HTTPException) as exc:
        await process_playlist_creation(
            playlist_name="test", user_id=USER_ID_EXAMPLE, db_session=db_session
        )
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == ("No tracks you have listened to were found.")


@pytest.mark.parametrize(
    "playlists, mocked_responses, expected_result",
    [
        (
            [{"uri": "spotify:playlist:1"}, {"uri": "spotify:playlist:2"}],
            [
                {
                    "tracks": {
                        "items": [
                            {"track": {"name": "Track A"}},
                            {"track": {"name": "Track B"}},
                        ]
                    }
                },
                {
                    "tracks": {
                        "items": [
                            {"track": {"name": "Track C"}},
                            {"track": {"name": "Track D"}},
                        ]
                    }
                },
            ],
            {"1": {"Track A", "Track B"}, "2": {"Track C", "Track D"}},
        )
    ],
)
@pytest.mark.asyncio
async def test_cache_playlist_tracks(
    playlists,
    mocked_responses,
    expected_result,
    db_session,
    mock_get_spotify_headers,
    mock_async_client_get,
    mock_redis,
):
    mock_request = httpx.Request("GET", "mock_request")
    mock_async_client_get.side_effect = [
        httpx.Response(status.HTTP_200_OK, json=mocked_response, request=mock_request)
        for mocked_response in mocked_responses
    ]
    result = await cache_playlist_tracks(playlists, USER_ID_EXAMPLE, db_session)
    assert result == expected_result
    assert mock_async_client_get.call_count == len(playlists)
