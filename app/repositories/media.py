from collections.abc import Iterable
from typing import Optional

from sqlalchemy import func, select

from app.models import Country, Episode, Genre, MediaContent, Movie
from app.patterns.builder import MediaQuery
from app.repositories.base import BaseRepository


class MediaRepository(BaseRepository[MediaContent]):
    model = MediaContent

    def get_movie(self, movie_id: int) -> Optional[Movie]:
        return self.db.get(Movie, movie_id)

    def get_episode(self, episode_id: int) -> Optional[Episode]:
        return self.db.get(Episode, episode_id)

    def find(self, query: MediaQuery) -> tuple[list[MediaContent], int]:
        """Return one page of media matching the query and the total number of matches."""
        stmt = select(MediaContent)
        if query.title:
            stmt = stmt.where(MediaContent.title.ilike(f"%{query.title}%"))
        if query.genre_id is not None:
            stmt = stmt.where(MediaContent.genres.any(Genre.id == query.genre_id))
        if query.year is not None:
            stmt = stmt.where(MediaContent.release_year == query.year)
        if query.country_id is not None:
            stmt = stmt.where(MediaContent.countries.any(Country.id == query.country_id))
        if query.media_type:
            stmt = stmt.where(MediaContent.kind == query.media_type)

        total = self.db.scalar(select(func.count()).select_from(stmt.subquery()))
        items = self.db.scalars(
            stmt.order_by(MediaContent.rating.desc(), MediaContent.title)
            .offset(query.offset)
            .limit(query.page_size)
        )
        return list(items), total

    def top_rated(self, limit: int = 10, exclude_ids: Iterable[int] = ()) -> list[MediaContent]:
        stmt = select(MediaContent).order_by(MediaContent.rating.desc()).limit(limit)
        exclude_ids = list(exclude_ids)
        if exclude_ids:
            stmt = stmt.where(MediaContent.id.not_in(exclude_ids))
        return list(self.db.scalars(stmt))

    def find_by_genres(
        self, genre_ids: Iterable[int], limit: int = 10, exclude_ids: Iterable[int] = ()
    ) -> list[MediaContent]:
        stmt = (
            select(MediaContent)
            .join(MediaContent.genres)
            .where(Genre.id.in_(list(genre_ids)))
            .distinct()
            .order_by(MediaContent.rating.desc())
            .limit(limit)
        )
        exclude_ids = list(exclude_ids)
        if exclude_ids:
            stmt = stmt.where(MediaContent.id.not_in(exclude_ids))
        return list(self.db.scalars(stmt))


class GenreRepository(BaseRepository[Genre]):
    model = Genre

    def get_all(self) -> list[Genre]:
        return list(self.db.scalars(select(Genre).order_by(Genre.name)))


class CountryRepository(BaseRepository[Country]):
    model = Country

    def get_all(self) -> list[Country]:
        return list(self.db.scalars(select(Country).order_by(Country.name)))