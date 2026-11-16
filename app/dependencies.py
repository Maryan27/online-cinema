from typing import Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.repositories import PlanRepository, UserRepository
from app.services.auth import AuthService
from app.services.exceptions import AuthenticationError, PermissionDeniedError

bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(UserRepository(db), PlanRepository(db))


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