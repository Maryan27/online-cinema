from typing import Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.repositories import PlanRepository, UserRepository
from app.services.auth import AuthService
from app.services.exceptions import AuthenticationError, PermissionDeniedError

from app.repositories import CountryRepository, GenreRepository, MediaRepository
from app.services.catalog import CatalogService

from app.patterns.adapter import FakePaymentProvider, PaymentGateway, PaymentProviderAdapter
from app.repositories import PaymentRepository, SubscriptionRepository
from app.services.subscription import SubscriptionService

from app.config import AD_VIDEO_URL
from app.patterns.proxy import IVideoStream, ProtectedVideoProxy, RealVideoStream
from app.repositories import WatchHistoryRepository
from app.services.video import VideoService

bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(UserRepository(db), PlanRepository(db))

def get_catalog_service(db: Session = Depends(get_db)) -> CatalogService:
    return CatalogService(MediaRepository(db), GenreRepository(db), CountryRepository(db))


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    if credentials is None:
        raise AuthenticationError("Not authenticated")
    return auth_service.get_current_user(credentials.credentials)


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin():
        raise PermissionDeniedError("Administrator access required")
    return user

def get_payment_gateway() -> PaymentGateway:
    return PaymentProviderAdapter(FakePaymentProvider())


def get_subscription_service(
    db: Session = Depends(get_db),
    gateway: PaymentGateway = Depends(get_payment_gateway),
) -> SubscriptionService:
    return SubscriptionService(
        gateway, SubscriptionRepository(db), PlanRepository(db), PaymentRepository(db)
    )

def get_video_stream(
    subscriptions: SubscriptionService = Depends(get_subscription_service),
) -> IVideoStream:
    return ProtectedVideoProxy(
        RealVideoStream(),
        state_provider=subscriptions.get_state,
        ad_url=AD_VIDEO_URL,
    )


def get_video_service(
    db: Session = Depends(get_db),
    stream: IVideoStream = Depends(get_video_stream),
) -> VideoService:
    return VideoService(stream, MediaRepository(db), WatchHistoryRepository(db))