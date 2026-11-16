from datetime import date, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, Response, UploadFile, status

from app.dependencies import get_admin_service, get_subscription_service, require_admin
from app.schemas.admin import (
    EpisodeCreate,
    MediaUpdate,
    MovieCreate,
    PlanUpdate,
    ReportResponse,
    SeasonCreate,
    SeriesCreate,
)
from app.schemas.media import EpisodeResponse, MediaDetailsResponse, SeasonResponse
from app.schemas.subscription import PlanResponse
from app.services.admin import AdminService
from app.services.subscription import SubscriptionService

DEFAULT_REPORT_DAYS = 30

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.post("/movies", response_model=MediaDetailsResponse, status_code=status.HTTP_201_CREATED)
def create_movie(data: MovieCreate, admin: AdminService = Depends(get_admin_service)):
    return MediaDetailsResponse.from_media(admin.create_movie(**data.model_dump()))


@router.post("/series", response_model=MediaDetailsResponse, status_code=status.HTTP_201_CREATED)
def create_series(data: SeriesCreate, admin: AdminService = Depends(get_admin_service)):
    return MediaDetailsResponse.from_media(admin.create_series(**data.model_dump()))


@router.post(
    "/series/{series_id}/seasons",
    response_model=SeasonResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_season(
    series_id: int, data: SeasonCreate, admin: AdminService = Depends(get_admin_service)
):
    return SeasonResponse.model_validate(admin.add_season(series_id, data.number))


@router.post(
    "/seasons/{season_id}/episodes",
    response_model=EpisodeResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_episode(
    season_id: int, data: EpisodeCreate, admin: AdminService = Depends(get_admin_service)
):
    return EpisodeResponse.model_validate(admin.add_episode(season_id, **data.model_dump()))


@router.put("/media/{media_id}", response_model=MediaDetailsResponse)
def update_media(
    media_id: int, data: MediaUpdate, admin: AdminService = Depends(get_admin_service)
):
    media = admin.update_media(media_id, **data.model_dump(exclude_unset=True))
    return MediaDetailsResponse.from_media(media)


@router.delete("/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media(media_id: int, admin: AdminService = Depends(get_admin_service)):
    admin.delete_media(media_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/media/{media_id}/poster", response_model=MediaDetailsResponse)
def upload_poster(
    media_id: int,
    poster: UploadFile = File(...),
    admin: AdminService = Depends(get_admin_service),
):
    media = admin.set_poster(media_id, poster.filename or "", poster.file.read())
    return MediaDetailsResponse.from_media(media)


@router.put("/plans/{plan_id}", response_model=PlanResponse)
def update_plan(plan_id: int, data: PlanUpdate, admin: AdminService = Depends(get_admin_service)):
    return admin.update_plan(plan_id, price=data.price, duration_days=data.duration_days)


@router.post("/subscriptions/expire-overdue")
def expire_overdue(subscriptions: SubscriptionService = Depends(get_subscription_service)):
    return {"expired": subscriptions.expire_overdue()}


@router.get("/reports/{report_type}", response_model=ReportResponse)
def get_report(
    report_type: Literal["popularity", "activity", "revenue"],
    start: Optional[date] = None,
    end: Optional[date] = None,
    admin: AdminService = Depends(get_admin_service),
):
    end = end or date.today()
    start = start or end - timedelta(days=DEFAULT_REPORT_DAYS)
    return admin.get_report(report_type, start, end)