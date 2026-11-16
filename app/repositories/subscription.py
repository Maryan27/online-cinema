from datetime import datetime
from typing import Optional

from sqlalchemy import select

from app.models import Payment, Subscription, SubscriptionPlan
from app.models.common import utcnow
from app.models.enums import PaymentStatus, PlanType
from app.repositories.base import BaseRepository


class PlanRepository(BaseRepository[SubscriptionPlan]):
    model = SubscriptionPlan

    def get_by_type(self, plan_type: PlanType) -> Optional[SubscriptionPlan]:
        return self.db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.type == plan_type))


class SubscriptionRepository(BaseRepository[Subscription]):
    model = Subscription

    def get_by_user(self, user_id: int) -> Optional[Subscription]:
        return self.db.scalar(select(Subscription).where(Subscription.user_id == user_id))

    def find_expired(self) -> list[Subscription]:
        stmt = select(Subscription).where(
            Subscription.expires_at.is_not(None),
            Subscription.expires_at <= utcnow(),
        )
        return list(self.db.scalars(stmt))


class PaymentRepository(BaseRepository[Payment]):
    model = Payment

    def list_successful(self, start: datetime, end: datetime) -> list[Payment]:
        stmt = (
            select(Payment)
            .where(
                Payment.status == PaymentStatus.SUCCESS,
                Payment.created_at >= start,
                Payment.created_at < end,
            )
            .order_by(Payment.created_at)
        )
        return list(self.db.scalars(stmt))