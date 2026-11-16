from app.models import Genre, Movie, User, WatchHistory
from app.models.enums import VideoQuality
from app.patterns.strategy import GenreBasedStrategy, TopRatedStrategy
from app.repositories import MediaRepository, WatchHistoryRepository
from app.services.recommendation import RecommendationService


def create_catalog(db):
    sports, drama = Genre(name="Sports"), Genre(name="Drama")
    movies = {
        "Derby Day": Movie(title="Derby Day", release_year=2020, duration_minutes=90,
                           rating=7.0, genres=[sports]),
        "Golden Boot": Movie(title="Golden Boot", release_year=2021, duration_minutes=95,
                             rating=8.0, genres=[sports]),
        "Rainy Tuesday": Movie(title="Rainy Tuesday", release_year=2019, duration_minutes=100,
                               rating=9.5, genres=[drama]),
    }
    user = User(email="fan@cinema.local", password_hash="x", name="Fan")
    db.add_all([*movies.values(), user])
    db.commit()
    return user, movies


def watch(db, user, movie):
    db.add(WatchHistory(user=user, movie=movie, quality=VideoQuality.Q720P))
    db.commit()


def make_service(db) -> RecommendationService:
    media_repo, history_repo = MediaRepository(db), WatchHistoryRepository(db)
    return RecommendationService(
        history_repo,
        GenreBasedStrategy(history_repo, media_repo),
        TopRatedStrategy(media_repo),
    )


def test_top_rated_strategy_orders_by_rating(db):
    user, _ = create_catalog(db)

    result = TopRatedStrategy(MediaRepository(db)).recommend(user, limit=2)

    assert [m.title for m in result] == ["Rainy Tuesday", "Golden Boot"]


def test_genre_based_strategy_recommends_unwatched_media_of_watched_genres(db):
    user, movies = create_catalog(db)
    watch(db, user, movies["Derby Day"])
    strategy = GenreBasedStrategy(WatchHistoryRepository(db), MediaRepository(db))

    result = strategy.recommend(user, limit=10)

    # Same genre, not watched yet; the higher-rated drama is not recommended
    assert [m.title for m in result] == ["Golden Boot"]


def test_service_uses_top_rated_for_user_without_history(db):
    user, _ = create_catalog(db)

    strategy, items = make_service(db).get_recommendations(user)

    assert strategy == "top_rated"
    assert items[0].title == "Rainy Tuesday"


def test_service_switches_to_genre_based_after_watching(db):
    user, movies = create_catalog(db)
    watch(db, user, movies["Derby Day"])

    strategy, items = make_service(db).get_recommendations(user)

    assert strategy == "genre_based"
    assert [m.title for m in items] == ["Golden Boot"]


def test_service_falls_back_to_top_rated_when_nothing_new_in_genres(db):
    user, movies = create_catalog(db)
    watch(db, user, movies["Derby Day"])
    watch(db, user, movies["Golden Boot"])

    strategy, _ = make_service(db).get_recommendations(user)

    assert strategy == "top_rated"