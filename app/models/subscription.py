from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SAEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.common import utcnow
from app.models.enums import PaymentStatus, PlanType

if TYPE_CHECKING:
    from app.models.user import User
    
class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[PlanType] = mapped_column(SAEnum(PlanType), unique=True)
    price_cents: Mapped[int] = mapped_column(default=0)
    duration_days: Mapped[Optional[int]] = mapped_column(default=None)

    @property
    def price(self) -> Decimal:
        return Decimal(self.price_cents) / 100


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    plan_id: Mapped[int] = mapped_column(ForeignKey("subscription_plans.id"))
    started_at: Mapped[datetime] = mapped_column(default=utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(default=None)

    user: Mapped["User"] = relationship(back_populates="subscription")
    plan: Mapped[SubscriptionPlan] = relationship()

    def is_active(self) -> bool:
        """Information Expert: the subscription itself knows whether it is active."""
        return self.expires_at is None or self.expires_at > utcnow()


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    plan_id: Mapped[int] = mapped_column(ForeignKey("subscription_plans.id"))
    amount_cents: Mapped[int]
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus), default=PaymentStatus.PENDING
    )
    transaction_id: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    user: Mapped["User"] = relationship(back_populates="payments")
    plan: Mapped[SubscriptionPlan] = relationship()