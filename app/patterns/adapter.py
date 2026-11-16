from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

if TYPE_CHECKING:
    from app.models import User


@dataclass(frozen=True)
class PaymentResult:
    success: bool
    transaction_id: Optional[str]
    message: str


class PaymentGateway(ABC):
    """Adapter pattern — Target: the payment interface our services depend on."""

    @abstractmethod
    def charge(self, user: "User", amount: Decimal) -> PaymentResult: ...


class FakePaymentProvider:
    """Adapter pattern — Adaptee: imitates a third-party payment API.

    Its interface is deliberately incompatible with ours: amounts in cents,
    raw dict responses and its own status values. Customers whose email
    starts with "declined" are rejected, to demonstrate failed payments.
    """

    def create_transaction(self, amount_cents: int, currency: str, metadata: dict) -> dict:
        if amount_cents <= 0:
            return {
                "status": "rejected",
                "error": {"code": "invalid_amount", "text": "Amount must be positive"},
            }
        if str(metadata.get("customer_email", "")).startswith("declined"):
            return {
                "status": "rejected",
                "error": {"code": "card_declined", "text": "Card was declined"},
            }
        return {
            "status": "approved",
            "id": f"txn_{uuid4().hex[:12]}",
            "amount": amount_cents,
            "currency": currency,
        }


class PaymentProviderAdapter(PaymentGateway):
    """Adapter pattern — Adapter: translates charge() into the provider's API."""

    def __init__(self, provider: FakePaymentProvider, currency: str = "UAH"):
        self.provider = provider
        self.currency = currency

    def charge(self, user: "User", amount: Decimal) -> PaymentResult:
        response = self.provider.create_transaction(
            amount_cents=int(amount * 100),
            currency=self.currency,
            metadata={"customer_id": user.id, "customer_email": user.email},
        )
        if response.get("status") == "approved":
            return PaymentResult(True, response["id"], "Payment approved")
        error = response.get("error", {})
        return PaymentResult(False, None, error.get("text", "Payment rejected"))