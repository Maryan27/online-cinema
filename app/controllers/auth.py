from fastapi import APIRouter, Depends, status

from app.dependencies import get_auth_service, get_current_user
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, auth_service: AuthService = Depends(get_auth_service)):
    user = auth_service.register(data.email, data.password, data.name)
    return UserResponse.from_user(user)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, auth_service: AuthService = Depends(get_auth_service)):
    return TokenResponse(access_token=auth_service.login(data.email, data.password))


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return UserResponse.from_user(user)