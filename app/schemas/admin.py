from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import VideoQuality


class MediaBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    release_year: int = Field(ge=1888, le=2100)
    rating: float = Field(0.0, ge=0, le=10)
    poster_url: Optional[str] = None
    genre_ids: list[int] = []
    country_ids: list[int] = []


class MovieCreate(MediaBase):
    duration_minutes: int = Field(ge=1)
    video_files: dict[VideoQuality, str] = {}


class SeriesCreate(MediaBase):
    pass


class MediaUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    release_year: Optional[int] = Field(None, ge=1888, le=2100)
    rating: Optional[float] = Field(None, ge=0, le=10)
    poster_url: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, ge=1)
    genre_ids: Optional[list[int]] = None
    country_ids: Optional[list[int]] = None


class SeasonCreate(BaseModel):
    number: int = Field(ge=1)


class EpisodeCreate(BaseModel):
    number: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    duration_minutes: int = Field(ge=1)
    video_files: dict[VideoQuality, str] = {}


class PlanUpdate(BaseModel):
    price: Optional[Decimal] = Field(None, ge=0)
    duration_days: Optional[int] = Field(None, ge=1)


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    report_type: str
    title: str
    period_start: date
    period_end: date
    columns: list[str]
    rows: list[dict[str, Any]]
    summary: dict[str, Any]
    generated_at: datetime