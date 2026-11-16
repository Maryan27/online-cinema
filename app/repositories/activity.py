from datetime import datetime
from typing import Optional

from sqlalchemy import select

from app.models import Favorite, WatchHistory
from app.repositories.base import BaseRepository


class WatchHistoryRepository(BaseRepository[WatchHistory]):
    model = WatchHistory

    def list_by_user(self, user_id: int, limit: Optional[int] = None) -> list[WatchHistory]:
        stmt = (
            select(WatchHistory)
            .where(WatchHistory.user_id == user_id)
            .order_by(WatchHistory.watched_at.desc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.db.scalars(stmt))

    def has_history(self, user_id: int) -> bool:
        stmt = select(WatchHistory.id).where(WatchHistory.user_id == user_id).limit(1)
        return self.db.scalar(stmt) is not None

    def list_in_period(self, start: datetime, end: datetime) -> list[WatchHistory]:
        stmt = (
            select(WatchHistory)
            .where(WatchHistory.watched_at >= start, WatchHistory.watched_at < end)
            .order_by(WatchHistory.watched_at)
        )
        return list(self.db.scalars(stmt))


class FavoriteRepository(BaseRepository[Favorite]):
    model = Favorite

    def list_by_user(self, user_id: int) -> list[Favorite]:
        stmt = (
            select(Favorite)
            .where(Favorite.user_id == user_id)
            .order_by(Favorite.added_at.desc())
        )
        return list(self.db.scalars(stmt))

    def find(self, user_id: int, media_id: int) -> Optional[Favorite]:
        return self.db.get(Favorite, (user_id, media_id))