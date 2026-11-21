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


def make_premium(premium_plan, days_left=10, auto_renew=True) -> Subscription:
    return Subscription(
        plan=premium_plan,
        started_at=utcnow() - timedelta(days=30 - days_left),
        expires_at=utcnow() + timedelta(days=days_left),
        auto_renew=auto_renew,
    )


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
    assert subscription.auto_renew


def test_expire_switches_premium_back_to_free():
    free_plan, premium_plan = make_plans()
    subscription = make_premium(premium_plan)

    subscription.expire(free_plan)

    assert isinstance(subscription.get_state(), FreeState)
    assert subscription.expires_at is None


def test_cancel_keeps_premium_until_the_end_of_the_paid_period():
    _, premium_plan = make_plans()
    subscription = make_premium(premium_plan)
    paid_until = subscription.expires_at

    subscription.cancel()

    assert isinstance(subscription.get_state(), PremiumState)
    assert subscription.expires_at == paid_until
    assert not subscription.auto_renew


def test_upgrade_of_cancelled_premium_turns_auto_renewal_back_on():
    _, premium_plan = make_plans()
    subscription = make_premium(premium_plan, auto_renew=False)
    paid_until = subscription.expires_at

    subscription.upgrade(premium_plan)

    assert subscription.auto_renew
    assert subscription.expires_at == paid_until


def test_renew_starts_a_new_paid_period():
    _, premium_plan = make_plans()
    subscription = make_premium(premium_plan, days_left=-1)

    subscription.renew(premium_plan)

    assert isinstance(subscription.get_state(), PremiumState)
    assert subscription.expires_at > utcnow()
    assert subscription.expires_at - subscription.started_at == timedelta(days=30)


def test_invalid_transitions_are_rejected_by_the_state():
    free_plan, premium_plan = make_plans()

    for action in (
        lambda s: s.expire(free_plan),
        lambda s: s.cancel(),
        lambda s: s.renew(premium_plan),
    ):
        with pytest.raises(InvalidStateTransition):
            action(Subscription(plan=free_plan))

    with pytest.raises(InvalidStateTransition):
        make_premium(premium_plan).upgrade(premium_plan)

    with pytest.raises(InvalidStateTransition):
        make_premium(premium_plan, auto_renew=False).cancel()