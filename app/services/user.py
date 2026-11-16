from typing import Optional

from app.models import Favorite, MediaContent, User
from app.repositories import FavoriteRepository, MediaRepository, UserRepository
from app.security import hash_password
from app.services.exceptions import NotFoundError


class UserService:
    def __init__(
        self,
        user_repo: UserRepository,
        favorite_repo: FavoriteRepository,
        media_repo: MediaRepository,
    ):
        self.user_repo = user_repo
        self.favorite_repo = favorite_repo
        self.media_repo = media_repo

    def update_profile(
        self, user: User, name: Optional[str] = None, password: Optional[str] = None
    ) -> User:
        if name is not None:
            user.name = name.strip()
        if password is not None:
            user.password_hash = hash_password(password)
        return self.user_repo.save(user)

    def get_favorites(self, user: User) -> list[MediaContent]:
        return [favorite.media for favorite in self.favorite_repo.list_by_user(user.id)]

    def add_favorite(self, user: User, media_id: int) -> None:
        """Idempotent: adding an item that is already a favourite changes nothing."""
        media = self.media_repo.get(media_id)
        if media is None:
            raise NotFoundError("Media not found")
        if self.favorite_repo.find(user.id, media_id) is None:
            self.favorite_repo.add(Favorite(user=user, media=media))

    def remove_favorite(self, user: User, media_id: int) -> None:
        """Idempotent: removing an item that is not a favourite changes nothing."""
        favorite = self.favorite_repo.find(user.id, media_id)
        if favorite is not None:
            self.favorite_repo.delete(favorite)