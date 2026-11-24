from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.common import utcnow
from app.models.enums import VideoQuality
from app.models.media import Episode, MediaContent, Movie, Playable

if TYPE_CHECKING:
    from app.models.user import User


class Favorite(Base):
    __tablename__ = "favorites"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    media_id: Mapped[int] = mapped_column(
        ForeignKey("media.id", ondelete="CASCADE"), primary_key=True
    )
    added_at: Mapped[datetime] = mapped_column(default=utcnow)

    user: Mapped["User"] = relationship(back_populates="favorites")
    media: Mapped[MediaContent] = relationship()


class WatchHistory(Base):
    __tablename__ = "watch_history"
    __table_args__ = (
        CheckConstraint(
            "(movie_id IS NULL) <> (episode_id IS NULL)",
            name="ck_watch_history_single_playable",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    movie_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), default=None
    )
    episode_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), default=None
    )
    quality: Mapped[VideoQuality] = mapped_column(SAEnum(VideoQuality))
    watched_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)

    user: Mapped["User"] = relationship(back_populates="watch_history")
    movie: Mapped[Optional[Movie]] = relationship()
    episode: Mapped[Optional[Episode]] = relationship()

    @property
    def playable(self) -> Playable:
        return self.movie if self.movie is not None else self.episode

    @property
    def media(self) -> MediaContent:
        """Catalog item that was watched: the movie itself or the episode's series."""
        if self.movie is not None:
            return self.movie
        return self.episode.season.series