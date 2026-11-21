from datetime import timedelta
from decimal import Decimal

import pytest

from app.models import Subscription, SubscriptionPlan, User
from app.models.common import utcnow
from app.models.enums import PaymentStatus, PlanType
from app.patterns.adapter import PaymentGateway, PaymentResult
from app.repositories import PaymentRepository, PlanRepository, SubscriptionRepository
from app.services.exceptions import BusinessRuleError
from app.services.subscription import SubscriptionService


class ApprovingGateway(PaymentGateway):
    def charge(self, user: User, amount: Decimal) -> PaymentResult:
        return PaymentResult(True, "test-txn", "Payment approved")


class DecliningGateway(PaymentGateway):
    def charge(self, user: User, amount: Decimal) -> PaymentResult:
        return PaymentResult(False, None, "Card was declined")


def create_free_user(db) -> User:
    free_plan = SubscriptionPlan(type=PlanType.FREE, price_cents=0, duration_days=None)
    premium_plan = SubscriptionPlan(type=PlanType.PREMIUM, price_cents=9900, duration_days=30)
    user = User(email="fan@cinema.local", password_hash="x", name="Fan")
    user.subscription = Subscription(plan=free_plan)
    db.add_all([free_plan, premium_plan, user])
    db.commit()
    return user


def make_service(db, gateway: PaymentGateway) -> SubscriptionService:
    return SubscriptionService(
        gateway, SubscriptionRepository(db), PlanRepository(db), PaymentRepository(db)
    )


def run_out_of_time(db, user: User) -> None:
    user.subscription.expires_at = utcnow() - timedelta(minutes=1)
    db.commit()


def test_successful_payment_upgrades_to_premium_and_records_payment(db):
    user = create_free_user(db)

    subscription = make_service(db, ApprovingGateway()).subscribe_premium(user)

    assert subscription.plan.type == PlanType.PREMIUM
    assert subscription.auto_renew
    [payment] = PaymentRepository(db).get_all()
    assert payment.status == PaymentStatus.SUCCESS
    assert payment.transaction_id == "test-txn"
    assert payment.amount_cents == 9900


def test_failed_payment_keeps_free_and_records_failed_payment(db):
    user = create_free_user(db)

    with pytest.raises(BusinessRuleError):
        make_service(db, DecliningGateway()).subscribe_premium(user)

    assert user.subscription.plan.type == PlanType.FREE
    [payment] = PaymentRepository(db).get_all()
    assert payment.status == PaymentStatus.FAILED


def test_overdue_premium_with_auto_renewal_is_renewed_and_charged(db):
    user = create_free_user(db)
    service = make_service(db, ApprovingGateway())
    service.subscribe_premium(user)
    run_out_of_time(db, user)

    subscription = service.get_subscription(user)

    assert subscription.plan.type == PlanType.PREMIUM
    assert subscription.expires_at > utcnow()
    assert len(PaymentRepository(db).get_all()) == 2


def test_failed_renewal_moves_premium_to_free(db):
    user = create_free_user(db)
    make_service(db, ApprovingGateway()).subscribe_premium(user)
    run_out_of_time(db, user)

    subscription = make_service(db, DecliningGateway()).get_subscription(user)

    assert subscription.plan.type == PlanType.FREE
    assert PaymentRepository(db).get_all()[-1].status == PaymentStatus.FAILED


def test_cancelled_premium_lasts_until_the_end_and_is_not_renewed(db):
    user = create_free_user(db)
    service = make_service(db, ApprovingGateway())
    service.subscribe_premium(user)

    subscription = service.cancel(user)

    assert subscription.plan.type == PlanType.PREMIUM  # the paid period is not lost
    assert not subscription.auto_renew

    run_out_of_time(db, user)
    assert service.get_subscription(user).plan.type == PlanType.FREE
    assert len(PaymentRepository(db).get_all()) == 1  # no renewal charge


def test_subscribing_again_resumes_cancelled_premium_without_payment(db):
    user = create_free_user(db)
    service = make_service(db, ApprovingGateway())
    service.subscribe_premium(user)
    service.cancel(user)

    subscription = service.subscribe_premium(user)

    assert subscription.auto_renew
    assert len(PaymentRepository(db).get_all()) == 1