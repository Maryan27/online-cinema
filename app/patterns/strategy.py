from abc import ABC, abstractmethod
from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import MediaContent, User
    from app.repositories import MediaRepository, WatchHistoryRepository

FAVOURITE_GENRES_COUNT = 3
CANDIDATES_LIMIT = 50


class RecommendationStrategy(ABC):
    """Strategy pattern — Strategy: a recommendation algorithm."""

    name: str

    @abstractmethod
    def recommend(self, user: "User", limit: int) -> list["MediaContent"]: ...


class TopRatedStrategy(RecommendationStrategy):
    """Concrete Strategy: the highest-rated media the user has not watched yet."""

    name = "top_rated"

    def __init__(self, media_repo: "MediaRepository", history_repo: "WatchHistoryRepository"):
        self.media_repo = media_repo
        self.history_repo = history_repo

    def recommend(self, user, limit) -> list["MediaContent"]:
        watched_ids = {entry.media.id for entry in self.history_repo.list_by_user(user.id)}
        items = self.media_repo.top_rated(limit, exclude_ids=watched_ids)
        return items or self.media_repo.top_rated(limit)


class GenreBasedStrategy(RecommendationStrategy):
    """Concrete Strategy: unwatched media from the user's most watched genres."""

    name = "genre_based"

    def __init__(self, history_repo: "WatchHistoryRepository", media_repo: "MediaRepository"):
        self.history_repo = history_repo
        self.media_repo = media_repo

    def recommend(self, user, limit) -> list["MediaContent"]:
        history = self.history_repo.list_by_user(user.id)
        watched = [entry.media for entry in history]  # an episode counts as its series
        watched_ids = {media.id for media in watched}
        genre_counts = Counter(genre.id for media in watched for genre in media.genres)
        if not genre_counts:
            return []

        favourite_genres = [genre_id for genre_id, _ in genre_counts.most_common(FAVOURITE_GENRES_COUNT)]
        candidates = self.media_repo.find_by_genres(
            favourite_genres, limit=CANDIDATES_LIMIT, exclude_ids=watched_ids
        )
        candidates.sort(
            key=lambda m: (sum(genre_counts[g.id] for g in m.genres), m.rating),
            reverse=True,
        )
        return candidates[:limit]