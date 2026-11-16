from decimal import Decimal

from app.models import User
from app.patterns.adapter import FakePaymentProvider, PaymentProviderAdapter


class SpyPaymentProvider(FakePaymentProvider):
    """Records how the adapter calls the third-party API."""

    def __init__(self):
        self.calls = []

    def create_transaction(self, amount_cents, currency, metadata):
        self.calls.append((amount_cents, currency, metadata))
        return super().create_transaction(amount_cents, currency, metadata)


def test_adapter_translates_charge_into_provider_api():
    spy = SpyPaymentProvider()
    adapter = PaymentProviderAdapter(spy)

    result = adapter.charge(User(id=5, email="striker@cinema.local"), Decimal("99.00"))

    assert result.success
    assert result.transaction_id.startswith("txn_")
    amount_cents, currency, metadata = spy.calls[0]
    assert amount_cents == 9900
    assert currency == "UAH"
    assert metadata["customer_email"] == "striker@cinema.local"


def test_adapter_translates_rejection_into_failed_result():
    adapter = PaymentProviderAdapter(FakePaymentProvider())

    result = adapter.charge(User(id=1, email="declined@cinema.local"), Decimal("99"))

    assert not result.success
    assert result.transaction_id is None
    assert result.message == "Card was declined"