from app.models import Payment, Subscription, SubscriptionPlan, User
from app.models.enums import PaymentStatus, PlanType
from app.patterns.adapter import PaymentGateway
from app.patterns.state import InvalidStateTransition, SubscriptionState
from app.repositories import PaymentRepository, PlanRepository, SubscriptionRepository
from app.services.exceptions import BusinessRuleError, NotFoundError


class SubscriptionService:
    def __init__(
        self,
        gateway: PaymentGateway,
        subscription_repo: SubscriptionRepository,
        plan_repo: PlanRepository,
        payment_repo: PaymentRepository,
    ):
        self.gateway = gateway
        self.subscription_repo = subscription_repo
        self.plan_repo = plan_repo
        self.payment_repo = payment_repo

    def list_plans(self) -> list[SubscriptionPlan]:
        return self.plan_repo.get_all()

    def get_subscription(self, user: User) -> Subscription:
        """Return the user's subscription, applying expiry if Premium has run out."""
        subscription = self.subscription_repo.get_by_user(user.id)
        if subscription is None:
            raise NotFoundError("Subscription not found")
        if subscription.plan.type == PlanType.PREMIUM and not subscription.is_active():
            subscription.expire(self._plan(PlanType.FREE))
            self.subscription_repo.save(subscription)
        return subscription

    def get_state(self, user: User) -> SubscriptionState:
        return self.get_subscription(user).get_state()

    def subscribe_premium(self, user: User) -> Subscription:
        subscription = self.get_subscription(user)
        if subscription.get_state().plan_type == PlanType.PREMIUM:
            raise BusinessRuleError("Premium subscription is already active")

        premium_plan = self._plan(PlanType.PREMIUM)
        payment = Payment(user=user, plan=premium_plan, amount_cents=premium_plan.price_cents)

        result = self.gateway.charge(user, premium_plan.price)  # Adapter
        if not result.success:
            payment.status = PaymentStatus.FAILED
            self.payment_repo.add(payment)
            raise BusinessRuleError(f"Payment failed: {result.message}")

        payment.status = PaymentStatus.SUCCESS
        payment.transaction_id = result.transaction_id
        try:
            subscription.upgrade(premium_plan)  # State: Free -> Premium
        except InvalidStateTransition as error:
            raise BusinessRuleError(str(error)) from error
        self.payment_repo.add(payment)  # commits the payment and the subscription change
        return subscription

    def cancel(self, user: User) -> Subscription:
        subscription = self.get_subscription(user)
        try:
            subscription.expire(self._plan(PlanType.FREE))  # State: Premium -> Free
        except InvalidStateTransition as error:
            raise BusinessRuleError(str(error)) from error
        return self.subscription_repo.save(subscription)

    def expire_overdue(self) -> int:
        """Move every overdue Premium subscription back to Free. Returns how many changed."""
        free_plan = self._plan(PlanType.FREE)
        expired = self.subscription_repo.find_expired()
        for subscription in expired:
            subscription.expire(free_plan)
        self.subscription_repo.db.commit()
        return len(expired)

    def _plan(self, plan_type: PlanType) -> SubscriptionPlan:
        plan = self.plan_repo.get_by_type(plan_type)
        if plan is None:
            raise NotFoundError(f"{plan_type.value} plan is not configured")
        return plan