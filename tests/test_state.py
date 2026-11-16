from datetime import timedelta

import pytest

from app.models import Subscription, SubscriptionPlan
from app.models.common import utcnow
from app.models.enums import PlanType, VideoQuality
from app.patterns.state import FreeState, InvalidStateTransition, PremiumState


def make_plans() -> tuple[SubscriptionPlan, SubscriptionPlan]:
    free_plan = SubscriptionPlan(type=PlanType.FREE, price_cents=0, duration_days=None)
    premium_plan = SubscriptionPlan(type=PlanType.PREMIUM, price_cents=9900, duration_days=30)
    return free_plan, premium_plan


def test_free_state_shows_ads_and_limits_quality_to_720p():
    free_plan, _ = make_plans()
    state = Subscription(plan=free_plan).get_state()

    assert isinstance(state, FreeState)
    assert state.requires_ad()
    assert state.allows_quality(VideoQuality.Q720P)
    assert not state.allows_quality(VideoQuality.Q1080P)


def test_premium_state_has_no_ads_and_allows_1080p():
    _, premium_plan = make_plans()
    state = Subscription(plan=premium_plan).get_state()

    assert isinstance(state, PremiumState)
    assert not state.requires_ad()
    assert state.allows_quality(VideoQuality.Q1080P)


def test_upgrade_switches_free_to_premium_for_plan_duration():
    free_plan, premium_plan = make_plans()
    subscription = Subscription(plan=free_plan)

    subscription.upgrade(premium_plan)

    assert isinstance(subscription.get_state(), PremiumState)
    assert subscription.expires_at - subscription.started_at == timedelta(days=30)


def test_expire_switches_premium_back_to_free():
    free_plan, premium_plan = make_plans()
    subscription = Subscription(plan=premium_plan, expires_at=utcnow() + timedelta(days=10))

    subscription.expire(free_plan)

    assert isinstance(subscription.get_state(), FreeState)
    assert subscription.expires_at is None


def test_invalid_transitions_are_rejected_by_the_state():
    free_plan, premium_plan = make_plans()

    with pytest.raises(InvalidStateTransition):
        Subscription(plan=free_plan).expire(free_plan)

    with pytest.raises(InvalidStateTransition):
        Subscription(plan=premium_plan).upgrade(premium_plan)