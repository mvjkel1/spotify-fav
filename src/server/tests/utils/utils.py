from sqlalchemy import insert
from sqlalchemy.ext.asyncio.session import AsyncSession

from app.db.models import Track, User, user_track_association_table
from tests.fixtures.constants import (
    EXAMPLE_TRACK_ID,
    SPOTIFY_USER_ID_EXAMPLE,
    TRACK_EXAMPLE_DB,
    USER_ID_EXAMPLE,
)


def get_model_attributes(instance):
    return {key: value for key, value in instance.__dict__.items() if not key.startswith("_")}


async def add_test_user(db_session: AsyncSession):
    test_user = User(
        id=USER_ID_EXAMPLE,
        spotify_uid=SPOTIFY_USER_ID_EXAMPLE,
        email="user@example.com",
        hashed_password="P!w!D",
    )
    db_session.add(test_user)
    await db_session.commit()


async def add_test_user_and_track(db_session: AsyncSession):
    await add_test_user(db_session)
    test_track = TRACK_EXAMPLE_DB
    db_session.add(test_track)
    await db_session.execute(
        insert(user_track_association_table).values(
            user_id=USER_ID_EXAMPLE, track_id=test_track.id, listened_count=1
        )
    )
    await db_session.commit()
