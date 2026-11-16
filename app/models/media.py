from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    Column,
    Enum as SAEnum,
    ForeignKey,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import VideoQuality

media_genres = Table(
    "media_genres",
    Base.metadata,
    Column("media_id", ForeignKey("media.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
)

media_countries = Table(
    "media_countries",
    Base.metadata,
    Column("media_id", ForeignKey("media.id", ondelete="CASCADE"), primary_key=True),
    Column("country_id", ForeignKey("countries.id", ondelete="CASCADE"), primary_key=True),
)


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

    media: Mapped[list["MediaContent"]] = relationship(
        secondary=media_genres, back_populates="genres"
    )


class Country(Base):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)

    media: Mapped[list["MediaContent"]] = relationship(
        secondary=media_countries, back_populates="countries"
    )


class MediaContent(Base):
    """Abstract catalog item: a Movie or a Series (joined-table inheritance)."""

    __tablename__ = "media"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    release_year: Mapped[int] = mapped_column(index=True)
    rating: Mapped[float] = mapped_column(default=0.0)
    poster_url: Mapped[Optional[str]] = mapped_column(String(500), default=None)

    genres: Mapped[list[Genre]] = relationship(
        secondary=media_genres, back_populates="media"
    )
    countries: Mapped[list[Country]] = relationship(
        secondary=media_countries, back_populates="media"
    )

    __mapper_args__ = {"polymorphic_on": "kind"}


class Playable:
    """Interface for anything that can be played (Movie, Episode).

    Implementing classes must define `video_files` and `duration_minutes`.
    """

    def get_video_files(self) -> list["VideoFile"]:
        return sorted(self.video_files, key=lambda v: v.quality.height)

    def get_video(self, quality: VideoQuality) -> Optional["VideoFile"]:
        return next((v for v in self.video_files if v.quality == quality), None)

    def get_duration(self) -> int:
        return self.duration_minutes


class Movie(MediaContent, Playable):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(
        ForeignKey("media.id", ondelete="CASCADE"), primary_key=True
    )
    duration_minutes: Mapped[int]

    video_files: Mapped[list["VideoFile"]] = relationship(
        back_populates="movie", cascade="all, delete-orphan"
    )

    __mapper_args__ = {"polymorphic_identity": "movie"}


class Series(MediaContent):
    __tablename__ = "series"

    id: Mapped[int] = mapped_column(
        ForeignKey("media.id", ondelete="CASCADE"), primary_key=True
    )

    seasons: Mapped[list["Season"]] = relationship(
        back_populates="series", cascade="all, delete-orphan", order_by="Season.number"
    )

    __mapper_args__ = {"polymorphic_identity": "series"}

    def add_season(self, number: int) -> "Season":
        """GRASP Creator: a series creates its own seasons."""
        season = Season(number=number)
        self.seasons.append(season)
        return season


class Season(Base):
    __tablename__ = "seasons"
    __table_args__ = (UniqueConstraint("series_id", "number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id", ondelete="CASCADE"))
    number: Mapped[int]

    series: Mapped[Series] = relationship(back_populates="seasons")
    episodes: Mapped[list["Episode"]] = relationship(
        back_populates="season", cascade="all, delete-orphan", order_by="Episode.number"
    )

    def add_episode(self, number: int, title: str, duration_minutes: int) -> "Episode":
        """GRASP Creator: a season creates its own episodes."""
        episode = Episode(number=number, title=title, duration_minutes=duration_minutes)
        self.episodes.append(episode)
        return episode


class Episode(Base, Playable):
    __tablename__ = "episodes"
    __table_args__ = (UniqueConstraint("season_id", "number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id", ondelete="CASCADE"))
    number: Mapped[int]
    title: Mapped[str] = mapped_column(String(200))
    duration_minutes: Mapped[int]

    season: Mapped[Season] = relationship(back_populates="episodes")
    video_files: Mapped[list["VideoFile"]] = relationship(
        back_populates="episode", cascade="all, delete-orphan"
    )


class VideoFile(Base):
    __tablename__ = "video_files"
    __table_args__ = (
        CheckConstraint(
            "(movie_id IS NULL) <> (episode_id IS NULL)",
            name="ck_video_file_single_owner",
        ),
        UniqueConstraint("movie_id", "quality"),
        UniqueConstraint("episode_id", "quality"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    quality: Mapped[VideoQuality] = mapped_column(SAEnum(VideoQuality))
    url: Mapped[str] = mapped_column(String(500))
    movie_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), default=None
    )
    episode_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), default=None
    )

    movie: Mapped[Optional[Movie]] = relationship(back_populates="video_files")
    episode: Mapped[Optional[Episode]] = relationship(back_populates="video_files")