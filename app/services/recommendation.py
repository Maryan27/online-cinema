from app.models import MediaContent, User
from app.patterns.strategy import GenreBasedStrategy, RecommendationStrategy, TopRatedStrategy
from app.repositories import WatchHistoryRepository

FALLBACK_SUFFIX = "_fallback"


class RecommendationService:
    """Strategy pattern — Context: picks a strategy and delegates the work to it."""

    def __init__(
        self,
        history_repo: WatchHistoryRepository,
        genre_strategy: GenreBasedStrategy,
        top_rated_strategy: TopRatedStrategy,
    ):
        self.history_repo = history_repo
        self.genre_strategy = genre_strategy
        self.top_rated_strategy = top_rated_strategy
        self.strategy: RecommendationStrategy = top_rated_strategy

    def set_strategy(self, strategy: RecommendationStrategy) -> None:
        self.strategy = strategy

    def get_recommendations(self, user: User, limit: int = 10) -> tuple[str, list[MediaContent]]:
        """Return the name of the strategy that was used and the recommended media.

        "top_rated_fallback" means the user has a history, but there is nothing new
        in their favourite genres, so the top-rated strategy was used instead.
        """
        if self.history_repo.has_history(user.id):
            self.set_strategy(self.genre_strategy)
        else:
            self.set_strategy(self.top_rated_strategy)

        items = self.strategy.recommend(user, limit)
        if not items and self.strategy is not self.top_rated_strategy:
            # Nothing new in the user's genres: fall back to the top-rated strategy
            self.set_strategy(self.top_rated_strategy)
            return self.strategy.name + FALLBACK_SUFFIX, self.strategy.recommend(user, limit)
        return self.strategy.name, items