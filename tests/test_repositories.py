from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Genre, Movie, Subscription, SubscriptionPlan, User, VideoFile, WatchHistory
from app.models.common import utcnow
from app.models.enums import PlanType, VideoQuality
from app.repositories import (
    MediaRepository,
    PlanRepository,
    SubscriptionRepository,
    UserRepository,
    WatchHistoryRepository,
)


def make_user(db, email="fan@cinema.local") -> User:
    return UserRepository(db).add(User(email=email, password_hash="x", name="Fan"))


def make_movie(db, title, rating, genres=()) -> Movie:
    return MediaRepository(db).add(
        Movie(
            title=title,
            release_year=2020,
            duration_minutes=90,
            rating=rating,
            genres=list(genres),
        )
    )


def make_premium_plan(db) -> SubscriptionPlan:
    return PlanRepository(db).add(
        SubscriptionPlan(type=PlanType.PREMIUM, price_cents=9900, duration_days=30)
    )


def test_get_user_by_email_is_case_insensitive(db):
    make_user(db, "striker@cinema.local")
    repo = UserRepository(db)

    assert repo.get_by_email("Striker@Cinema.local").name == "Fan"
    assert repo.get_by_email("missing@cinema.local") is None


def test_get_plan_by_type(db):
    make_premium_plan(db)

    plan = PlanRepository(db).get_by_type(PlanType.PREMIUM)

    assert plan.price_cents == 9900
    assert plan.price == 99


def test_top_rated_is_sorted_and_respects_exclusions(db):
    make_movie(db, "Derby Day", 6.0)
    best = make_movie(db, "Golden Boot", 9.0)
    make_movie(db, "Offside", 7.5)
    repo = MediaRepository(db)

    assert [m.title for m in repo.top_rated()] == ["Golden Boot", "Offside", "Derby Day"]
    assert best not in repo.top_rated(exclude_ids=[best.id])


def test_find_by_genres_returns_only_matching_media(db):
    sports, drama = Genre(name="Sports"), Genre(name="Drama")
    make_movie(db, "Final Whistle", 8.0, [sports])
    make_movie(db, "Rainy Tuesday", 9.0, [drama])

    result = MediaRepository(db).find_by_genres([sports.id])

    assert [m.title for m in result] == ["Final Whistle"]


def test_find_expired_subscriptions(db):
    user = make_user(db)
    plan = make_premium_plan(db)
    repo = SubscriptionRepository(db)
    repo.add(Subscription(user=user, plan=plan, expires_at=utcnow() - timedelta(days=1)))

    expired = repo.find_expired()

    assert len(expired) == 1
    assert not expired[0].is_active()


def test_has_history(db):
    user = make_user(db)
    movie = make_movie(db, "Penalty Kick", 7.0)
    repo = WatchHistoryRepository(db)

    assert not repo.has_history(user.id)
    repo.add(WatchHistory(user=user, movie=movie, quality=VideoQuality.Q720P))
    assert repo.has_history(user.id)


def test_video_file_must_belong_to_exactly_one_owner(db):
    db.add(VideoFile(quality=VideoQuality.Q720P, url="/media/videos/orphan.mp4"))

    with pytest.raises(IntegrityError):
        db.commit()