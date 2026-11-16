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


def test_successful_payment_upgrades_to_premium_and_records_payment(db):
    user = create_free_user(db)

    subscription = make_service(db, ApprovingGateway()).subscribe_premium(user)

    assert subscription.plan.type == PlanType.PREMIUM
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


def test_overdue_premium_is_moved_to_free_on_access(db):
    user = create_free_user(db)
    service = make_service(db, ApprovingGateway())
    service.subscribe_premium(user)
    user.subscription.expires_at = utcnow() - timedelta(minutes=1)  # time has run out
    db.commit()

    subscription = service.get_subscription(user)

    assert subscription.plan.type == PlanType.FREE