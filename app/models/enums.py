from enum import Enum


class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"


class PlanType(str, Enum):
    FREE = "free"
    PREMIUM = "premium"


class VideoQuality(str, Enum):
    Q480P = "480p"
    Q720P = "720p"
    Q1080P = "1080p"

    @property
    def height(self) -> int:
        """Vertical resolution, used to compare qualities (e.g. 720 < 1080)."""
        return int(self.value.removesuffix("p"))


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"