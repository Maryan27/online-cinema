from typing import Literal, Optional

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user, get_video_service
from app.models import User
from app.models.enums import VideoQuality
from app.schemas.video import StreamResponse
from app.services.video import VideoService

router = APIRouter(prefix="/api/play", tags=["player"])


@router.get("/{kind}/{playable_id}", response_model=StreamResponse)
def play(
    kind: Literal["movie", "episode"],
    playable_id: int,
    quality: Optional[VideoQuality] = None,
    user: User = Depends(get_current_user),
    video_service: VideoService = Depends(get_video_service),
):
    return video_service.play(user, kind, playable_id, quality)