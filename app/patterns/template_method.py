from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING, Any

from app.models.common import utcnow

if TYPE_CHECKING:
    from app.repositories import PaymentRepository, WatchHistoryRepository

REPORT_TYPES = ("popularity", "activity", "revenue")


@dataclass(frozen=True)
class ReportResult:
    report_type: str
    title: str
    period_start: date
    period_end: date
    columns: list[str]
    rows: list[dict[str, Any]]
    summary: dict[str, Any]
    generated_at: datetime


class Report(ABC):
    """Template Method pattern — AbstractClass.

    generate() is the template method: it fixes the order of the steps,
    and subclasses only fill in the steps that differ.
    """

    report_type: str
    title: str
    columns: list[str]

    def generate(self, start: date, end: date) -> ReportResult:
        period_start = datetime.combine(start, time.min)
        period_end = datetime.combine(end + timedelta(days=1), time.min)  # end date is inclusive
        data = self.fetch_data(period_start, period_end)
        rows = self.aggregate(data)
        summary = self.summarize(data, rows)
        return self.build_result(rows, summary, start, end)

    @abstractmethod
    def fetch_data(self, start: datetime, end: datetime) -> list: ...

    @abstractmethod
    def aggregate(self, data: list) -> list[dict[str, Any]]: ...

    def summarize(self, data: list, rows: list[dict[str, Any]]) -> dict[str, Any]:
        """Hook: an optional step that subclasses may override to add totals."""
        return {}

    def build_result(self, rows, summary, start: date, end: date) -> ReportResult:
        return ReportResult(
            report_type=self.report_type,
            title=self.title,
            period_start=start,
            period_end=end,
            columns=list(self.columns),
            rows=rows,
            summary=summary,
            generated_at=utcnow(),
        )


class PopularityReport(Report):
    """Concrete Class: the most watched titles and genres."""

    report_type = "popularity"
    title = "Most popular movies and genres"
    columns = ["title", "kind", "views", "viewers"]

    def __init__(self, history_repo: "WatchHistoryRepository"):
        self.history_repo = history_repo

    def fetch_data(self, start, end):
        return self.history_repo.list_in_period(start, end)

    def aggregate(self, data):
        views: Counter = Counter()
        viewers: dict[int, set[int]] = defaultdict(set)
        media_by_id = {}
        for entry in data:
            media = entry.media  # an episode counts as its series
            media_by_id[media.id] = media
            views[media.id] += 1
            viewers[media.id].add(entry.user_id)
        return [
            {
                "title": media_by_id[media_id].title,
                "kind": media_by_id[media_id].kind,
                "views": count,
                "viewers": len(viewers[media_id]),
            }
            for media_id, count in views.most_common()
        ]

    def summarize(self, data, rows):
        genre_views = Counter(genre.name for entry in data for genre in entry.media.genres)
        return {
            "total_views": len(data),
            "top_genres": [
                {"genre": name, "views": count} for name, count in genre_views.most_common(5)
            ],
        }


class UserActivityReport(Report):
    """Concrete Class: how actively each user watches."""

    report_type = "activity"
    title = "User activity"
    columns = ["user", "email", "views", "titles_watched", "last_watched"]

    def __init__(self, history_repo: "WatchHistoryRepository"):
        self.history_repo = history_repo

    def fetch_data(self, start, end):
        return self.history_repo.list_in_period(start, end)

    def aggregate(self, data):
        by_user: dict[int, list] = defaultdict(list)
        for entry in data:
            by_user[entry.user_id].append(entry)

        rows = []
        for entries in by_user.values():
            user = entries[0].user
            rows.append(
                {
                    "user": user.name,
                    "email": user.email,
                    "views": len(entries),
                    "titles_watched": len({e.media.id for e in entries}),
                    "last_watched": max(e.watched_at for e in entries).isoformat(timespec="minutes"),
                }
            )
        return sorted(rows, key=lambda row: row["views"], reverse=True)

    def summarize(self, data, rows):
        return {
            "active_users": len(rows),
            "total_views": len(data),
            "average_views_per_user": round(len(data) / len(rows), 1) if rows else 0,
        }


class RevenueReport(Report):
    """Concrete Class: subscription revenue by month."""

    report_type = "revenue"
    title = "Subscription revenue"
    columns = ["month", "payments", "revenue"]

    def __init__(self, payment_repo: "PaymentRepository"):
        self.payment_repo = payment_repo

    def fetch_data(self, start, end):
        return self.payment_repo.list_successful(start, end)

    def aggregate(self, data):
        months: dict[str, list] = defaultdict(list)
        for payment in data:
            months[payment.created_at.strftime("%Y-%m")].append(payment)
        return [
            {
                "month": month,
                "payments": len(payments),
                "revenue": sum(p.amount_cents for p in payments) / 100,
            }
            for month, payments in sorted(months.items())
        ]

    def summarize(self, data, rows):
        return {
            "total_revenue": sum(p.amount_cents for p in data) / 100,
            "payments": len(data),
            "paying_users": len({p.user_id for p in data}),
        }


class ReportFactory:
    """Simple Factory (not a GoF pattern): creates a report object by its type name."""

    def __init__(self, history_repo: "WatchHistoryRepository", payment_repo: "PaymentRepository"):
        self.history_repo = history_repo
        self.payment_repo = payment_repo

    def create(self, report_type: str) -> Report:
        if report_type == "popularity":
            return PopularityReport(self.history_repo)
        if report_type == "activity":
            return UserActivityReport(self.history_repo)
        if report_type == "revenue":
            return RevenueReport(self.payment_repo)
        raise ValueError(f"Unknown report type: {report_type}")