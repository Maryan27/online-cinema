from typing import Optional

from app.models import Country, Genre, MediaContent
from app.patterns.builder import MediaQueryBuilder
from app.repositories import CountryRepository, GenreRepository, MediaRepository
from app.services.exceptions import BusinessRuleError, NotFoundError


class CatalogService:
    def __init__(
        self,
        media_repo: MediaRepository,
        genre_repo: GenreRepository,
        country_repo: CountryRepository,
    ):
        self.media_repo = media_repo
        self.genre_repo = genre_repo
        self.country_repo = country_repo

    def search(
        self,
        *,
        title: Optional[str] = None,
        genre_id: Optional[int] = None,
        year: Optional[int] = None,
        country_id: Optional[int] = None,
        media_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 12,
    ) -> tuple[list[MediaContent], int]:
        """Builder pattern — Director: decides how the search query is assembled."""
        try:
            query = (
                MediaQueryBuilder()
                .title(title)
                .genre(genre_id)
                .year(year)
                .country(country_id)
                .media_type(media_type)
                .paginate(page, page_size)
                .build()
            )
        except ValueError as error:
            raise BusinessRuleError(str(error)) from error
        return self.media_repo.find(query)

    def get_details(self, media_id: int) -> MediaContent:
        media = self.media_repo.get(media_id)
        if media is None:
            raise NotFoundError("Media not found")
        return media

    def list_genres(self) -> list[Genre]:
        return self.genre_repo.get_all()

    def list_countries(self) -> list[Country]:
        return self.country_repo.get_all()