from typing import Literal, Optional

from app.models import Playable, User, WatchHistory
from app.models.enums import VideoQuality
from app.patterns.proxy import IVideoStream, StreamResult, VideoUnavailableError
from app.repositories import MediaRepository, WatchHistoryRepository
from app.services.exceptions import NotFoundError

PlayableKind = Literal["movie", "episode"]


class VideoService:
    def __init__(
        self,
        stream: IVideoStream,
        media_repo: MediaRepository,
        history_repo: WatchHistoryRepository,
    ):
        self.stream = stream  
        self.media_repo = media_repo
        self.history_repo = history_repo

    def play(
        self,
        user: User,
        kind: PlayableKind,
        playable_id: int,
        quality: Optional[VideoQuality] = None,
    ) -> StreamResult:
        playable = self._find_playable(kind, playable_id)
        try:
            result = self.stream.get_stream(user, playable, quality)
        except VideoUnavailableError as error:
            raise NotFoundError(str(error)) from error

        entry = WatchHistory(user=user, quality=result.quality)
        if kind == "movie":
            entry.movie = playable
        else:
            entry.episode = playable
        self.history_repo.add(entry)
        return result

    def _find_playable(self, kind: PlayableKind, playable_id: int) -> Playable:
        if kind == "movie":
            playable = self.media_repo.get_movie(playable_id)
        else:
            playable = self.media_repo.get_episode(playable_id)
        if playable is None:
            raise NotFoundError(f"{kind.capitalize()} not found")
        return playable