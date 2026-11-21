from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models import Subscription
from app.models.enums import PlanType, VideoQuality


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: PlanType
    price: float
    duration_days: Optional[int]


class SubscriptionResponse(BaseModel):
    plan: PlanType
    started_at: datetime
    expires_at: Optional[datetime]
    auto_renew: bool
    requires_ad: bool
    max_quality: VideoQuality

    @classmethod
    def from_subscription(cls, subscription: Subscription) -> "SubscriptionResponse":
        state = subscription.get_state()
        return cls(
            plan=subscription.plan.type,
            started_at=subscription.started_at,
            expires_at=subscription.expires_at,
            auto_renew=subscription.auto_renew,
            requires_ad=state.requires_ad(),
            max_quality=state.max_quality(),
        )