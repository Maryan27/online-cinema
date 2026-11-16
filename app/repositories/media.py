from collections.abc import Iterable
from typing import Optional

from sqlalchemy import select

from app.models import Country, Episode, Genre, MediaContent, Movie
from app.repositories.base import BaseRepository


class MediaRepository(BaseRepository[MediaContent]):
    model = MediaContent

    def get_movie(self, movie_id: int) -> Optional[Movie]:
        return self.db.get(Movie, movie_id)

    def get_episode(self, episode_id: int) -> Optional[Episode]:
        return self.db.get(Episode, episode_id)

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