from dataclasses import dataclass
from typing import Optional

MEDIA_TYPES = ("movie", "series")
MAX_PAGE_SIZE = 50


@dataclass(frozen=True)
class MediaQuery:
    """Builder pattern — Product: an immutable set of catalog search criteria."""

    title: Optional[str] = None
    genre_id: Optional[int] = None
    year: Optional[int] = None
    country_id: Optional[int] = None
    media_type: Optional[str] = None
    page: int = 1
    page_size: int = 12

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class MediaQueryBuilder:
    """Builder pattern — Builder: assembles a MediaQuery step by step.

    Every step is optional and empty values are ignored, so request
    parameters can be passed in as they are.
    """

    def __init__(self) -> None:
        self._params: dict = {}

    def title(self, text: Optional[str]) -> "MediaQueryBuilder":
        if text and text.strip():
            self._params["title"] = text.strip()
        return self

    def genre(self, genre_id: Optional[int]) -> "MediaQueryBuilder":
        if genre_id is not None:
            self._params["genre_id"] = genre_id
        return self

    def year(self, year: Optional[int]) -> "MediaQueryBuilder":
        if year is not None:
            self._params["year"] = year
        return self

    def country(self, country_id: Optional[int]) -> "MediaQueryBuilder":
        if country_id is not None:
            self._params["country_id"] = country_id
        return self

    def media_type(self, kind: Optional[str]) -> "MediaQueryBuilder":
        if kind is not None:
            if kind not in MEDIA_TYPES:
                raise ValueError(f"Unknown media type: {kind}")
            self._params["media_type"] = kind
        return self

    def paginate(self, page: int, page_size: int) -> "MediaQueryBuilder":
        self._params["page"] = max(page, 1)
        self._params["page_size"] = min(max(page_size, 1), MAX_PAGE_SIZE)
        return self

    def build(self) -> MediaQuery:
        return MediaQuery(**self._params)