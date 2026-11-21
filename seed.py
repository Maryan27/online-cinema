"""Recreate the database and fill it with demo data.

Usage:
    python seed.py
"""

import random
import re
from datetime import timedelta

from app.database import Base, SessionLocal, engine
from app.models import (
    Country,
    Favorite,
    Genre,
    Movie,
    Payment,
    Series,
    Subscription,
    SubscriptionPlan,
    User,
    VideoFile,
    WatchHistory,
)
from app.models.common import utcnow
from app.models.enums import PaymentStatus, PlanType, Role, VideoQuality
from app.security import hash_password

GENRES = ["Action", "Animation", "Comedy", "Drama", "Fantasy", "Sci-Fi", "Sports"]
COUNTRIES = ["Netherlands", "Ukraine", "USA", "United Kingdom", "Spain", "Brazil"]

OPEN_MOVIES = [
    ("Big Buck Bunny", 2008, 10, 6.4, ["Animation", "Comedy"], ["Netherlands"],
     "A giant, gentle rabbit takes revenge on three rodents who bully him."),
    ("Elephants Dream", 2006, 11, 6.2, ["Animation", "Sci-Fi"], ["Netherlands"],
     "Two men explore a strange machine world that keeps changing around them."),
    ("Sintel", 2010, 15, 7.4, ["Animation", "Fantasy"], ["Netherlands"],
     "A lonely girl travels far to find the baby dragon she once raised."),
    ("Tears of Steel", 2012, 12, 6.0, ["Sci-Fi", "Action"], ["Netherlands"],
     "A group of scientists tries to save the world from rogue robots."),
    ("Cosmos Laundromat", 2015, 12, 7.0, ["Animation", "Comedy", "Fantasy"], ["Netherlands"],
     "A gloomy sheep meets a mysterious salesman who offers him new lives."),
    ("Spring", 2019, 8, 7.1, ["Animation", "Fantasy"], ["Netherlands"],
     "A shepherd girl and her dog face ancient spirits to bring back spring."),
    ("Agent 327: Operation Barbershop", 2017, 4, 7.3, ["Animation", "Action", "Comedy"],
     ["Netherlands"], "A secret agent goes undercover in a suspicious barbershop."),
]

FOOTBALL_MOVIES = [
    ("Last Minute Goal", 2021, 12, 7.9, ["Sports", "Drama"], ["Ukraine"],
     "A substitute striker gets one minute on the pitch to save his club from relegation.", 3),
    ("The Twelfth Man", 2019, 10, 7.5, ["Sports", "Comedy"], ["United Kingdom", "Spain"],
     "A stubborn fan swaps places with the coach of his favourite team for one match.", 0),
    ("Golden Goal Night", 2024, 14, 7.7, ["Sports", "Drama"], ["Ukraine"],
     "Two old rivals meet again in a cup final that is decided by a golden goal in extra time.", 2),
    ("Offside Trap", 2022, 11, 7.2, ["Sports", "Comedy"], ["Spain"],
     "A rookie linesman raises his flag once and turns a village derby into a national scandal.", 4),
    ("Derby Night", 2020, 13, 7.6, ["Sports", "Action"], ["Brazil"],
     "The fiercest derby in Rio is played on a night when nobody in the city is allowed to lose.", 5),
    ("Golden Boot", 2023, 12, 6.9, ["Sports", "Drama"], ["USA"],
     "A veteran striker chases the league scoring record in the last season of his career.", 1),
    ("The Last Transfer", 2018, 10, 6.8, ["Sports", "Drama"], ["United Kingdom"],
     "On deadline day an agent has twelve hours to close the deal that will save his career.", 6),
    ("Underdogs", 2025, 12, 8.0, ["Sports", "Comedy"], ["Ukraine"],
     "A school team from Lviv enters a national tournament with second-hand boots and big dreams.", 0),
]

SERIES = {
    "title": "Extra Time",
    "year": 2023,
    "rating": 8.1,
    "genres": ["Sports", "Drama", "Comedy"],
    "countries": ["Ukraine"],
    "description": "A small-town Ukrainian football club fights to survive its first "
                   "season in the second league.",
    "seasons": [
        ["Pre-season", "Derby Day", "Red Card"],
        ["Transfer Window", "Penalty Shootout", "Final Whistle"],
    ],
}

FOOTBALL_CLIPS = ["football-1", "football-2", "football-3"]

VIEWERS = ["Goalkeeper", "Defender", "Midfielder", "Winger", "Striker", "Coach"]

FREE_QUALITIES = [VideoQuality.Q480P, VideoQuality.Q720P]


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def make_video_files(clip: str) -> list[VideoFile]:
    return [
        VideoFile(quality=q, url=f"/media/videos/{clip}_{q.value}.mp4")
        for q in VideoQuality
    ]


def seed() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    random.seed(17)

    with SessionLocal() as db:
        free_plan = SubscriptionPlan(type=PlanType.FREE, price_cents=0, duration_days=None)
        premium_plan = SubscriptionPlan(type=PlanType.PREMIUM, price_cents=9900, duration_days=30)
        db.add_all([free_plan, premium_plan])

        genres = {name: Genre(name=name) for name in GENRES}
        countries = {name: Country(name=name) for name in COUNTRIES}
        db.add_all([*genres.values(), *countries.values()])

        def make_movie(title, year, minutes, rating, genre_names, country_names,
                       description, clip) -> Movie:
            return Movie(
                title=title,
                release_year=year,
                duration_minutes=minutes,
                rating=rating,
                description=description,
                poster_url=f"/media/posters/{slugify(title)}.jpg",
                genres=[genres[n] for n in genre_names],
                countries=[countries[n] for n in country_names],
                video_files=make_video_files(clip),
            )

        movies = [make_movie(*m, clip=slugify(m[0])) for m in OPEN_MOVIES]
        movies += [
            make_movie(*m[:7], clip=FOOTBALL_CLIPS[m[7] % len(FOOTBALL_CLIPS)])
            for m in FOOTBALL_MOVIES
        ]
        db.add_all(movies)

        series = Series(
            title=SERIES["title"],
            release_year=SERIES["year"],
            rating=SERIES["rating"],
            description=SERIES["description"],
            poster_url=f"/media/posters/{slugify(SERIES['title'])}.jpg",
            genres=[genres[n] for n in SERIES["genres"]],
            countries=[countries[n] for n in SERIES["countries"]],
        )
        episodes = []
        for season_number, titles in enumerate(SERIES["seasons"], start=1):
            season = series.add_season(season_number)
            for episode_number, title in enumerate(titles, start=1):
                episode = season.add_episode(episode_number, title, duration_minutes=10)
                episode.video_files = make_video_files(
                    FOOTBALL_CLIPS[len(episodes) % len(FOOTBALL_CLIPS)]
                )
                episodes.append(episode)
        db.add(series)

        playables = [*movies, *episodes]

        def create_user(email, password, name, role=Role.USER, premium=False) -> User:
            now = utcnow()
            user = User(
                email=email,
                password_hash=hash_password(password),
                name=name,
                role=role,
                created_at=now - timedelta(days=random.randint(90, 150)),
            )
            if premium:
                months = random.randint(1, 3)
                start = now - timedelta(days=random.randint(1, 25))
                user.subscription = Subscription(
                    plan=premium_plan,
                    started_at=start,
                    expires_at=start + timedelta(days=premium_plan.duration_days),
                )
                for i in range(months):
                    user.payments.append(
                        Payment(
                            plan=premium_plan,
                            amount_cents=premium_plan.price_cents,
                            status=PaymentStatus.SUCCESS,
                            transaction_id=f"demo-{slugify(email)}-{i}",
                            created_at=start - timedelta(days=30 * i),
                        )
                    )
            else:
                user.subscription = Subscription(plan=free_plan, started_at=user.created_at)
            db.add(user)
            return user

        def add_history(user: User, count: int, premium: bool) -> None:
            qualities = list(VideoQuality) if premium else FREE_QUALITIES
            for _ in range(count):
                item = random.choice(playables)
                entry = WatchHistory(
                    quality=random.choice(qualities),
                    watched_at=utcnow()
                    - timedelta(days=random.randint(0, 60), minutes=random.randint(0, 1440)),
                )
                if isinstance(item, Movie):
                    entry.movie = item
                else:
                    entry.episode = item
                user.watch_history.append(entry)

        create_user("admin@cinema.local", "admin123", "Administrator", role=Role.ADMIN)

        create_user("user@cinema.local", "user1234", "Demo User")

        premium_user = create_user(
            "premium@cinema.local", "premium123", "Premium User", premium=True
        )
        add_history(premium_user, 15, premium=True)
        premium_user.favorites.extend(Favorite(media=m) for m in movies[-2:])

        for i, name in enumerate(VIEWERS, start=1):
            is_premium = i % 2 == 0
            viewer = create_user(
                f"viewer{i}@cinema.local", "password123", name, premium=is_premium
            )
            add_history(viewer, random.randint(5, 20), premium=is_premium)

        db.commit()

        print(
            f"Seeded: {db.query(Movie).count()} movies, 1 series ({len(episodes)} episodes), "
            f"{db.query(User).count()} users, {db.query(WatchHistory).count()} history entries, "
            f"{db.query(Payment).count()} payments."
        )


if __name__ == "__main__":
    seed()