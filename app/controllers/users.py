from fastapi import APIRouter, Depends, Query, Response, status

from app.dependencies import get_current_user, get_recommendation_service, get_user_service
from app.models import User
from app.schemas.media import MediaShortResponse, RecommendationsResponse
from app.schemas.user import ProfileUpdateRequest, UserResponse
from app.services.recommendation import RecommendationService
from app.services.user import UserService

router = APIRouter(prefix="/api/users/me", tags=["users"])


@router.get("", response_model=UserResponse)
def get_profile(user: User = Depends(get_current_user)):
    return UserResponse.from_user(user)


@router.put("", response_model=UserResponse)
def update_profile(
    data: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    updated = user_service.update_profile(user, name=data.name, password=data.password)
    return UserResponse.from_user(updated)


@router.get("/favorites", response_model=list[MediaShortResponse])
def list_favorites(
    user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    return user_service.get_favorites(user)


@router.put("/favorites/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
def add_favorite(
    media_id: int,
    user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    user_service.add_favorite(user, media_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/favorites/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(
    media_id: int,
    user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    user_service.remove_favorite(user, media_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/recommendations", response_model=RecommendationsResponse)
def get_recommendations(
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_user),
    recommendations: RecommendationService = Depends(get_recommendation_service),
):
    strategy, items = recommendations.get_recommendations(user, limit)
    return RecommendationsResponse(
        strategy=strategy,
        items=[MediaShortResponse.model_validate(m) for m in items],
    )