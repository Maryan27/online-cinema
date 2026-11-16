from app.models import Movie, User, VideoFile
from app.models.enums import VideoQuality
from app.patterns.proxy import ProtectedVideoProxy, RealVideoStream
from app.patterns.state import FreeState, PremiumState

AD_URL = "/media/videos/ad.mp4"
FAN = User(id=1, email="fan@cinema.local", name="Fan")


def make_movie() -> Movie:
    return Movie(
        title="Last Minute Goal",
        release_year=2021,
        duration_minutes=12,
        video_files=[
            VideoFile(quality=q, url=f"/media/videos/goal_{q.value}.mp4") for q in VideoQuality
        ],
    )


def make_proxy(state) -> ProtectedVideoProxy:
    return ProtectedVideoProxy(RealVideoStream(), state_provider=lambda user: state, ad_url=AD_URL)


def test_real_stream_alone_performs_no_access_checks():
    result = RealVideoStream().get_stream(FAN, make_movie(), VideoQuality.Q1080P)

    assert result.quality == VideoQuality.Q1080P
    assert result.ad_url is None


def test_proxy_downgrades_free_user_to_720p_and_adds_ad():
    result = make_proxy(FreeState()).get_stream(FAN, make_movie(), VideoQuality.Q1080P)

    assert result.quality == VideoQuality.Q720P
    assert result.stream_url.endswith("_720p.mp4")
    assert result.ad_url == AD_URL
    assert result.downgraded
    assert VideoQuality.Q1080P not in result.available_qualities


def test_proxy_keeps_allowed_quality_for_free_user():
    result = make_proxy(FreeState()).get_stream(FAN, make_movie(), VideoQuality.Q480P)

    assert result.quality == VideoQuality.Q480P
    assert not result.downgraded


def test_proxy_gives_premium_user_1080p_without_ad():
    result = make_proxy(PremiumState()).get_stream(FAN, make_movie(), VideoQuality.Q1080P)

    assert result.quality == VideoQuality.Q1080P
    assert result.ad_url is None
    assert not result.downgraded
    assert result.available_qualities == list(VideoQuality)


def test_proxy_uses_best_allowed_quality_by_default():
    assert make_proxy(FreeState()).get_stream(FAN, make_movie(), None).quality == VideoQuality.Q720P
    assert make_proxy(PremiumState()).get_stream(FAN, make_movie(), None).quality == VideoQuality.Q1080P