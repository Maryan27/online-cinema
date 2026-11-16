from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_catalog_service
from app.schemas.media import (
    CountryResponse,
    GenreResponse,
    MediaDetailsResponse,
    MediaPage,
    MediaShortResponse,
)
from app.services.catalog import CatalogService

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/media", response_model=MediaPage)
def search_media(
    title: Optional[str] = None,
    genre_id: Optional[int] = None,
    year: Optional[int] = None,
    country_id: Optional[int] = None,
    media_type: Optional[Literal["movie", "series"]] = Query(None, alias="type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    catalog: CatalogService = Depends(get_catalog_service),
):
    items, total = catalog.search(
        title=title,
        genre_id=genre_id,
        year=year,
        country_id=country_id,
        media_type=media_type,
        page=page,
        page_size=page_size,
    )
    return MediaPage(
        items=[MediaShortResponse.model_validate(m) for m in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/media/{media_id}", response_model=MediaDetailsResponse)
def get_media(media_id: int, catalog: CatalogService = Depends(get_catalog_service)):
    return MediaDetailsResponse.from_media(catalog.get_details(media_id))


@router.get("/genres", response_model=list[GenreResponse])
def list_genres(catalog: CatalogService = Depends(get_catalog_service)):
    return catalog.list_genres()


@router.get("/countries", response_model=list[CountryResponse])
def list_countries(catalog: CatalogService = Depends(get_catalog_service)):
    return catalog.list_countries()