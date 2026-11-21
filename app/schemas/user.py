from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models import User
from app.models.enums import PlanType, Role
from app.schemas.auth import PASSWORD_MIN_LENGTH


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: Role
    plan: Optional[PlanType]
    premium_until: Optional[datetime]

    @classmethod
    def from_user(cls, user: User) -> "UserResponse":
        subscription = user.subscription
        return cls(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            plan=subscription.plan.type if subscription else None,
            premium_until=subscription.expires_at if subscription else None,
        )


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    password: Optional[str] = Field(None, min_length=PASSWORD_MIN_LENGTH, max_length=128)