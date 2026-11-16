from datetime import date, datetime

import pytest

from app.models import Genre, Movie, Payment, Series, SubscriptionPlan, User, WatchHistory
from app.models.enums import PaymentStatus, PlanType, VideoQuality
from app.patterns.template_method import (
    PopularityReport,
    Report,
    ReportFactory,
    RevenueReport,
    UserActivityReport,
)
from app.repositories import PaymentRepository, WatchHistoryRepository

NOVEMBER = (date(2026, 11, 1), date(2026, 11, 30))
MATCH_NIGHT = datetime(2026, 11, 10, 20, 0)


class RecordingReport(Report):
    """Minimal concrete report that records how the template method calls it."""

    report_type = "test"
    title = "Test report"
    columns = ["value"]

    def __init__(self):
        self.calls = []

    def fetch_data(self, start, end):
        self.calls.append(("fetch_data", start, end))
        return [1, 2, 3]

    def aggregate(self, data):
        self.calls.append(("aggregate",))
        return [{"value": sum(data)}]


def make_user(email: str, name: str) -> User:
    return User(email=email, password_hash="x", name=name)


def test_template_method_runs_steps_in_fixed_order():
    report = RecordingReport()

    result = report.generate(*NOVEMBER)

    assert [call[0] for call in report.calls] == ["fetch_data", "aggregate"]
    _, start, end = report.calls[0]
    assert start == datetime(2026, 11, 1)
    assert end == datetime(2026, 12, 1)  # the end date is inclusive
    assert result.rows == [{"value": 6}]
    assert result.summary == {}  # the hook was not overridden


def test_popularity_report_counts_episode_views_for_its_series(db):
    sports = Genre(name="Sports")
    movie = Movie(title="Last Minute Goal", release_year=2021, duration_minutes=12,
                  rating=7.9, genres=[sports])
    series = Series(title="Extra Time", release_year=2023, rating=8.1, genres=[sports])
    episode = series.add_season(1).add_episode(1, "Derby Day", 10)
    fan, ultras = make_user("fan@cinema.local", "Fan"), make_user("ultras@cinema.local", "Ultras")
    db.add_all([
        movie, series, fan, ultras,
        WatchHistory(user=fan, episode=episode, quality=VideoQuality.Q720P, watched_at=MATCH_NIGHT),
        WatchHistory(user=ultras, episode=episode, quality=VideoQuality.Q720P, watched_at=MATCH_NIGHT),
        WatchHistory(user=fan, movie=movie, quality=VideoQuality.Q480P, watched_at=MATCH_NIGHT),
    ])
    db.commit()

    result = PopularityReport(WatchHistoryRepository(db)).generate(*NOVEMBER)

    assert result.rows[0] == {"title": "Extra Time", "kind": "series", "views": 2, "viewers": 2}
    assert result.rows[1]["title"] == "Last Minute Goal"
    assert result.summary["top_genres"] == [{"genre": "Sports", "views": 3}]


def test_user_activity_report_sorts_users_by_views(db):
    movie = Movie(title="Penalty Kick", release_year=2020, duration_minutes=10, rating=7.0)
    fan, ultras = make_user("fan@cinema.local", "Fan"), make_user("ultras@cinema.local", "Ultras")
    db.add_all([
        movie, fan, ultras,
        WatchHistory(user=ultras, movie=movie, quality=VideoQuality.Q720P, watched_at=MATCH_NIGHT),
        WatchHistory(user=fan, movie=movie, quality=VideoQuality.Q720P, watched_at=MATCH_NIGHT),
        WatchHistory(user=fan, movie=movie, quality=VideoQuality.Q720P, watched_at=MATCH_NIGHT),
    ])
    db.commit()

    result = UserActivityReport(WatchHistoryRepository(db)).generate(*NOVEMBER)

    assert [row["user"] for row in result.rows] == ["Fan", "Ultras"]
    assert result.rows[0]["views"] == 2
    assert result.rows[0]["titles_watched"] == 1
    assert result.summary == {"active_users": 2, "total_views": 3, "average_views_per_user": 1.5}


def test_revenue_report_groups_by_month_and_ignores_other_payments(db):
    plan = SubscriptionPlan(type=PlanType.PREMIUM, price_cents=9900, duration_days=30)
    fan = make_user("fan@cinema.local", "Fan")

    def payment(when: datetime, status=PaymentStatus.SUCCESS) -> Payment:
        return Payment(user=fan, plan=plan, amount_cents=9900, status=status, created_at=when)

    db.add_all([
        plan, fan,
        payment(datetime(2026, 9, 5)),
        payment(datetime(2026, 10, 5)),
        payment(datetime(2026, 10, 20)),
        payment(datetime(2026, 10, 21), PaymentStatus.FAILED),  # failed: not revenue
        payment(datetime(2026, 12, 1)),                         # outside the period
    ])
    db.commit()

    result = RevenueReport(PaymentRepository(db)).generate(date(2026, 9, 1), date(2026, 10, 31))

    assert result.rows == [
        {"month": "2026-09", "payments": 1, "revenue": 99.0},
        {"month": "2026-10", "payments": 2, "revenue": 198.0},
    ]
    assert result.summary == {"total_revenue": 297.0, "payments": 3, "paying_users": 1}


def test_report_factory_creates_reports_by_type(db):
    factory = ReportFactory(WatchHistoryRepository(db), PaymentRepository(db))

    assert isinstance(factory.create("popularity"), PopularityReport)
    assert isinstance(factory.create("activity"), UserActivityReport)
    assert isinstance(factory.create("revenue"), RevenueReport)
    with pytest.raises(ValueError):
        factory.create("weather")