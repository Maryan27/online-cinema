from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Optional

from app.config import MEDIA_DIR
from app.models import Episode, MediaContent, Movie, Season, Series, SubscriptionPlan, VideoFile
from app.models.enums import PlanType, VideoQuality
from app.patterns.template_method import ReportFactory, ReportResult
from app.repositories import CountryRepository, GenreRepository, MediaRepository, PlanRepository
from app.services.exceptions import AlreadyExistsError, BusinessRuleError, NotFoundError

POSTER_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class AdminService:
    def __init__(
        self,
        media_repo: MediaRepository,
        genre_repo: GenreRepository,
        country_repo: CountryRepository,
        plan_repo: PlanRepository,
        report_factory: ReportFactory,
    ):
        self.media_repo = media_repo
        self.genre_repo = genre_repo
        self.country_repo = country_repo
        self.plan_repo = plan_repo
        self.report_factory = report_factory


    def create_movie(
        self,
        *,
        genre_ids: list[int],
        country_ids: list[int],
        video_files: dict[VideoQuality, str],
        **fields,
    ) -> Movie:
        movie = Movie(**fields)
        self._set_dictionaries(movie, genre_ids, country_ids)
        movie.video_files = self._make_video_files(video_files)
        return self.media_repo.add(movie)

    def create_series(self, *, genre_ids: list[int], country_ids: list[int], **fields) -> Series:
        series = Series(**fields)
        self._set_dictionaries(series, genre_ids, country_ids)
        return self.media_repo.add(series)

    def add_season(self, series_id: int, number: int) -> Season:
        series = self.media_repo.get_series(series_id)
        if series is None:
            raise NotFoundError("Series not found")
        if any(season.number == number for season in series.seasons):
            raise AlreadyExistsError(f"Season {number} already exists")
        season = series.add_season(number)  # GRASP Creator
        self.media_repo.save(series)
        return season

    def add_episode(
        self,
        season_id: int,
        *,
        number: int,
        title: str,
        duration_minutes: int,
        video_files: dict[VideoQuality, str],
    ) -> Episode:
        season = self.media_repo.get_season(season_id)
        if season is None:
            raise NotFoundError("Season not found")
        if any(episode.number == number for episode in season.episodes):
            raise AlreadyExistsError(f"Episode {number} already exists in this season")
        episode = season.add_episode(number, title, duration_minutes)  # GRASP Creator
        episode.video_files = self._make_video_files(video_files)
        self.media_repo.save(season)
        return episode

    def update_media(
        self,
        media_id: int,
        *,
        genre_ids: Optional[list[int]] = None,
        country_ids: Optional[list[int]] = None,
        duration_minutes: Optional[int] = None,
        **fields,
    ) -> MediaContent:
        media = self._get_media(media_id)
        for name, value in fields.items():
            if value is not None:
                setattr(media, name, value)
        if duration_minutes is not None:
            if not isinstance(media, Movie):
                raise BusinessRuleError("Only movies have a duration")
            media.duration_minutes = duration_minutes
        self._set_dictionaries(media, genre_ids, country_ids)
        return self.media_repo.save(media)

    def delete_media(self, media_id: int) -> None:
        self.media_repo.delete(self._get_media(media_id))

    def set_poster(self, media_id: int, filename: str, content: bytes) -> MediaContent:
        media = self._get_media(media_id)
        suffix = Path(filename).suffix.lower()
        if suffix not in POSTER_EXTENSIONS:
            raise BusinessRuleError("Poster must be a JPG, PNG or WEBP image")
        posters_dir = MEDIA_DIR / "posters"
        posters_dir.mkdir(parents=True, exist_ok=True)
        path = posters_dir / f"media-{media.id}{suffix}"
        path.write_bytes(content)
        media.poster_url = f"/media/posters/{path.name}"
        return self.media_repo.save(media)


    def update_plan(
        self,
        plan_id: int,
        price: Optional[Decimal] = None,
        duration_days: Optional[int] = None,
    ) -> SubscriptionPlan:
        plan = self.plan_repo.get(plan_id)
        if plan is None:
            raise NotFoundError("Plan not found")
        if plan.type == PlanType.FREE and (price not in (None, 0) or duration_days is not None):
            raise BusinessRuleError("The free plan always costs 0 and never expires")
        if price is not None:
            plan.price_cents = int(round(price * 100))
        if duration_days is not None:
            plan.duration_days = duration_days
        return self.plan_repo.save(plan)


    def get_report(self, report_type: str, start: date, end: date) -> ReportResult:
        if start > end:
            raise BusinessRuleError("The start date must not be later than the end date")
        try:
            report = self.report_factory.create(report_type)
        except ValueError as error:
            raise NotFoundError(str(error)) from error
        return report.generate(start, end)  # Template Method

    def _get_media(self, media_id: int) -> MediaContent:
        media = self.media_repo.get(media_id)
        if media is None:
            raise NotFoundError("Media not found")
        return media

    def _set_dictionaries(
        self,
        media: MediaContent,
        genre_ids: Optional[list[int]],
        country_ids: Optional[list[int]],
    ) -> None:
        if genre_ids is not None:
            genres = self.genre_repo.get_many(genre_ids)
            if len(genres) != len(set(genre_ids)):
                raise NotFoundError("Unknown genre id")
            media.genres = genres
        if country_ids is not None:
            countries = self.country_repo.get_many(country_ids)
            if len(countries) != len(set(country_ids)):
                raise NotFoundError("Unknown country id")
            media.countries = countries

    @staticmethod
    def _make_video_files(urls: dict[VideoQuality, str]) -> list[VideoFile]:
        return [VideoFile(quality=quality, url=url) for quality, url in urls.items()]