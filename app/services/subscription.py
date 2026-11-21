from app.models import Payment, Subscription, SubscriptionPlan, User
from app.models.enums import PaymentStatus, PlanType
from app.patterns.adapter import PaymentGateway, PaymentResult
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
        """Return the user's subscription, renewing or expiring Premium if its period is over."""
        subscription = self.subscription_repo.get_by_user(user.id)
        if subscription is None:
            raise NotFoundError("Subscription not found")
        if subscription.plan.type == PlanType.PREMIUM and not subscription.is_active():
            self._process_expiry(subscription)
            self.subscription_repo.save(subscription)
        return subscription

    def get_state(self, user: User) -> SubscriptionState:
        return self.get_subscription(user).get_state()

    def subscribe_premium(self, user: User) -> Subscription:
        subscription = self.get_subscription(user)
        premium_plan = self._plan(PlanType.PREMIUM)

        if subscription.get_state().plan_type == PlanType.PREMIUM:
            # The current period is already paid: only turn auto-renewal back on, no charge
            try:
                subscription.upgrade(premium_plan)  # State: Premium (cancelled) -> Premium
            except InvalidStateTransition as error:
                raise BusinessRuleError(str(error)) from error
            return self.subscription_repo.save(subscription)

        result = self._charge(user, premium_plan)  # Adapter
        if not result.success:
            raise BusinessRuleError(f"Payment failed: {result.message}")
        try:
            subscription.upgrade(premium_plan)  # State: Free -> Premium
        except InvalidStateTransition as error:
            raise BusinessRuleError(str(error)) from error
        return self.subscription_repo.save(subscription)

    def cancel(self, user: User) -> Subscription:
        """Turn off auto-renewal: Premium keeps working until the end of the paid period."""
        subscription = self.get_subscription(user)
        try:
            subscription.cancel()  # State: Premium stays Premium until expires_at
        except InvalidStateTransition as error:
            raise BusinessRuleError(str(error)) from error
        return self.subscription_repo.save(subscription)

    def expire_overdue(self) -> int:
        """Renew or expire every overdue Premium subscription. Returns how many moved to Free."""
        overdue = self.subscription_repo.find_expired()
        for subscription in overdue:
            self._process_expiry(subscription)
        self.subscription_repo.db.commit()
        return sum(1 for subscription in overdue if subscription.plan.type == PlanType.FREE)

    def _process_expiry(self, subscription: Subscription) -> None:
        """The paid period is over: renew it if auto-renewal is on and the payment succeeds."""
        premium_plan = self._plan(PlanType.PREMIUM)
        if subscription.auto_renew and self._charge(subscription.user, premium_plan).success:
            subscription.renew(premium_plan)  # State: Premium -> Premium, next period
        else:
            subscription.expire(self._plan(PlanType.FREE))  # State: Premium -> Free

    def _charge(self, user: User, plan: SubscriptionPlan) -> PaymentResult:
        """Charge the user through the payment gateway and record the payment."""
        result = self.gateway.charge(user, plan.price)
        self.payment_repo.add(
            Payment(
                user=user,
                plan=plan,
                amount_cents=plan.price_cents,
                status=PaymentStatus.SUCCESS if result.success else PaymentStatus.FAILED,
                transaction_id=result.transaction_id,
            )
        )
        return result

    def _plan(self, plan_type: PlanType) -> SubscriptionPlan:
        plan = self.plan_repo.get_by_type(plan_type)
        if plan is None:
            raise NotFoundError(f"{plan_type.value} plan is not configured")
        return plan