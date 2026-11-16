from app.models import Subscription, User
from app.models.enums import PlanType
from app.repositories import PlanRepository, UserRepository
from app.security import create_access_token, decode_access_token, hash_password, verify_password
from app.services.exceptions import AlreadyExistsError, AuthenticationError, NotFoundError


class AuthService:
    def __init__(self, user_repo: UserRepository, plan_repo: PlanRepository):
        self.user_repo = user_repo
        self.plan_repo = plan_repo

    def register(self, email: str, password: str, name: str) -> User:
        email = email.lower()
        if self.user_repo.get_by_email(email) is not None:
            raise AlreadyExistsError("A user with this email already exists")

        free_plan = self.plan_repo.get_by_type(PlanType.FREE)
        if free_plan is None:
            raise NotFoundError("Free plan is not configured")

        user = User(email=email, password_hash=hash_password(password), name=name)
        user.subscription = Subscription(plan=free_plan)  # every new user starts on Free
        return self.user_repo.add(user)

    def login(self, email: str, password: str) -> str:
        user = self.user_repo.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password")
        return create_access_token(user.id)

    def get_current_user(self, token: str) -> User:
        user_id = decode_access_token(token)
        user = self.user_repo.get(user_id) if user_id is not None else None
        if user is None:
            raise AuthenticationError("Invalid or expired token")
        return user