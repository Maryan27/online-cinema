from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Optional

from app.models.enums import VideoQuality

if TYPE_CHECKING:
    from app.models import Playable, User
    from app.patterns.state import SubscriptionState


class VideoUnavailableError(Exception):
    """The requested video file does not exist."""


@dataclass(frozen=True)
class StreamResult:
    stream_url: str
    quality: VideoQuality
    ad_url: Optional[str]
    available_qualities: list[VideoQuality]
    downgraded: bool = False


class IVideoStream(ABC):
    """Proxy pattern — Subject: common interface of the real stream and the proxy."""

    @abstractmethod
    def get_stream(
        self, user: "User", playable: "Playable", quality: Optional[VideoQuality]
    ) -> StreamResult: ...


class RealVideoStream(IVideoStream):
    """Proxy pattern — RealSubject: knows where video files are. No access checks."""

    def get_stream(self, user, playable, quality) -> StreamResult:
        files = playable.get_video_files()
        if not files:
            raise VideoUnavailableError("No video files for this item")
        video = playable.get_video(quality) if quality else files[-1]
        if video is None:
            raise VideoUnavailableError(f"Video is not available in {quality.value}")
        return StreamResult(
            stream_url=video.url,
            quality=video.quality,
            ad_url=None,
            available_qualities=[f.quality for f in files],
        )


class ProtectedVideoProxy(IVideoStream):
    """Proxy pattern — Protection Proxy.

    Has the same interface as RealVideoStream and controls access to it
    according to the user's subscription state (State pattern):
    limits the quality and adds an ad for free users.
    """

    def __init__(
        self,
        real_stream: RealVideoStream,
        state_provider: Callable[["User"], "SubscriptionState"],
        ad_url: str,
    ):
        self.real_stream = real_stream
        self.state_provider = state_provider
        self.ad_url = ad_url

    def get_stream(self, user, playable, quality) -> StreamResult:
        state = self.state_provider(user)
        allowed = [
            f.quality for f in playable.get_video_files() if state.allows_quality(f.quality)
        ]
        if not allowed:
            raise VideoUnavailableError("No video is available for your subscription")

        requested = quality or state.max_quality()
        granted = self._resolve_quality(requested, allowed)
        result = self.real_stream.get_stream(user, playable, granted)

        return replace(
            result,
            ad_url=self.ad_url if state.requires_ad() else None,
            available_qualities=allowed,
            downgraded=granted != requested,
        )

    @staticmethod
    def _resolve_quality(requested: VideoQuality, allowed: list[VideoQuality]) -> VideoQuality:
        """Use the requested quality if allowed, otherwise the best allowed one below it."""
        if requested in allowed:
            return requested
        lower = [q for q in allowed if q.height <= requested.height]
        return max(lower or allowed, key=lambda q: q.height)