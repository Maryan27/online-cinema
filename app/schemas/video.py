from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.enums import VideoQuality


class StreamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stream_url: str
    quality: VideoQuality
    ad_url: Optional[str]
    available_qualities: list[VideoQuality]
    downgraded: bool