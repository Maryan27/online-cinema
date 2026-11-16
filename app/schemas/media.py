from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models import MediaContent, Movie, Series
from app.models.enums import VideoQuality


class GenreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class CountryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class MediaShortResponse(BaseModel):
    """Catalog card: enough data to show a poster tile."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    title: str
    release_year: int
    rating: float
    poster_url: Optional[str]
    genres: list[GenreResponse]


class MediaPage(BaseModel):
    items: list[MediaShortResponse]
    total: int
    page: int
    page_size: int


class EpisodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: int
    title: str
    duration_minutes: int


class SeasonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: int
    episodes: list[EpisodeResponse]


class MediaDetailsResponse(MediaShortResponse):
    """Full media card. Video URLs are deliberately NOT exposed here:
    they are issued only by the video proxy after checking the subscription."""

    description: str
    countries: list[CountryResponse]
    duration_minutes: Optional[int] = None
    available_qualities: list[VideoQuality] = []
    seasons: list[SeasonResponse] = []

    @classmethod
    def from_media(cls, media: MediaContent) -> "MediaDetailsResponse":
        extra: dict = {}
        if isinstance(media, Movie):
            extra["duration_minutes"] = media.duration_minutes
            extra["available_qualities"] = [v.quality for v in media.get_video_files()]
        elif isinstance(media, Series):
            extra["seasons"] = [SeasonResponse.model_validate(s) for s in media.seasons]

        return cls(
            id=media.id,
            kind=media.kind,
            title=media.title,
            release_year=media.release_year,
            rating=media.rating,
            poster_url=media.poster_url,
            genres=[GenreResponse.model_validate(g) for g in media.genres],
            description=media.description,
            countries=[CountryResponse.model_validate(c) for c in media.countries],
            **extra,
        )