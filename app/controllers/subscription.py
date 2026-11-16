from fastapi import APIRouter, Depends

from app.dependencies import get_current_user, get_subscription_service
from app.models import User
from app.schemas.subscription import PlanResponse, SubscriptionResponse
from app.services.subscription import SubscriptionService

router = APIRouter(prefix="/api", tags=["subscription"])


@router.get("/plans", response_model=list[PlanResponse])
def list_plans(service: SubscriptionService = Depends(get_subscription_service)):
    return service.list_plans()


@router.get("/subscription", response_model=SubscriptionResponse)
def get_my_subscription(
    user: User = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
):
    return SubscriptionResponse.from_subscription(service.get_subscription(user))


@router.post("/subscription/premium", response_model=SubscriptionResponse)
def subscribe_premium(
    user: User = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
):
    return SubscriptionResponse.from_subscription(service.subscribe_premium(user))


@router.delete("/subscription/premium", response_model=SubscriptionResponse)
def cancel_premium(
    user: User = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
):
    return SubscriptionResponse.from_subscription(service.cancel(user))