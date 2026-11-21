from abc import ABC, abstractmethod
from datetime import timedelta
from typing import TYPE_CHECKING

from app.models.common import utcnow
from app.models.enums import PlanType, VideoQuality

if TYPE_CHECKING:
    from app.models import Subscription, SubscriptionPlan


class InvalidStateTransition(Exception):
    """The requested transition is not allowed from the current state."""


class SubscriptionState(ABC):
    """State pattern — State: behaviour that depends on the subscription type."""

    plan_type: PlanType

    @abstractmethod
    def requires_ad(self) -> bool: ...

    @abstractmethod
    def max_quality(self) -> VideoQuality: ...

    @abstractmethod
    def upgrade(
        self, subscription: "Subscription", premium_plan: "SubscriptionPlan"
    ) -> "SubscriptionState": ...

    @abstractmethod
    def expire(
        self, subscription: "Subscription", free_plan: "SubscriptionPlan"
    ) -> "SubscriptionState": ...

    @abstractmethod
    def cancel(self, subscription: "Subscription") -> "SubscriptionState": ...

    @abstractmethod
    def renew(
        self, subscription: "Subscription", premium_plan: "SubscriptionPlan"
    ) -> "SubscriptionState": ...

    def allows_quality(self, quality: VideoQuality) -> bool:
        return quality.height <= self.max_quality().height


class FreeState(SubscriptionState):
    """Concrete State: free access with ads, up to 720p."""

    plan_type = PlanType.FREE

    def requires_ad(self) -> bool:
        return True

    def max_quality(self) -> VideoQuality:
        return VideoQuality.Q720P

    def upgrade(self, subscription, premium_plan) -> SubscriptionState:
        now = utcnow()
        subscription.plan = premium_plan
        subscription.started_at = now
        subscription.expires_at = now + timedelta(days=premium_plan.duration_days)
        subscription.auto_renew = True
        return state_for(PlanType.PREMIUM)

    def expire(self, subscription, free_plan) -> SubscriptionState:
        raise InvalidStateTransition("Subscription is already free")

    def cancel(self, subscription) -> SubscriptionState:
        raise InvalidStateTransition("Subscription is already free")

    def renew(self, subscription, premium_plan) -> SubscriptionState:
        raise InvalidStateTransition("Only a Premium subscription can be renewed")


class PremiumState(SubscriptionState):
    """Concrete State: no ads, up to 1080p."""

    plan_type = PlanType.PREMIUM

    def requires_ad(self) -> bool:
        return False

    def max_quality(self) -> VideoQuality:
        return VideoQuality.Q1080P

    def upgrade(self, subscription, premium_plan) -> SubscriptionState:
        if subscription.auto_renew:
            raise InvalidStateTransition("Premium subscription is already active")
        # Cancelled but still paid: subscribing again only turns auto-renewal back on
        subscription.auto_renew = True
        return self

    def expire(self, subscription, free_plan) -> SubscriptionState:
        subscription.plan = free_plan
        subscription.started_at = utcnow()
        subscription.expires_at = None
        subscription.auto_renew = True
        return state_for(PlanType.FREE)

    def cancel(self, subscription) -> SubscriptionState:
        if not subscription.auto_renew:
            raise InvalidStateTransition("Premium subscription is already cancelled")
        # Premium stays until the end of the paid period, it just will not be renewed
        subscription.auto_renew = False
        return self

    def renew(self, subscription, premium_plan) -> SubscriptionState:
        now = utcnow()
        subscription.started_at = now
        subscription.expires_at = now + timedelta(days=premium_plan.duration_days)
        return self


_STATES: dict[PlanType, SubscriptionState] = {
    PlanType.FREE: FreeState(),
    PlanType.PREMIUM: PremiumState(),
}


def state_for(plan_type: PlanType) -> SubscriptionState:
    return _STATES[plan_type]