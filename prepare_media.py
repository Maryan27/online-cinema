"""Prepare demo video files in three qualities plus the ad clip.

For every clip used in seed.py (open movies and football stock clips):
  * if media/sources/<slug>.<ext> exists, a fragment of up to 60 seconds is cut from it
    (open movies from 0:30, short football stock clips from the start);
  * otherwise the clip borrows one of the real sources that do exist, so every title
    plays real footage; a test pattern is generated only when media/sources is empty.
The ad clip is copied from media/sources/ad.mp4 when it exists.

Requires ffmpeg on PATH.

Usage:
    python prepare_media.py
"""

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from app.config import MEDIA_DIR
from app.models.enums import VideoQuality
from seed import FOOTBALL_CLIPS, OPEN_MOVIES, slugify

SOURCES_DIR = MEDIA_DIR / "sources"
VIDEOS_DIR = MEDIA_DIR / "videos"

CLIP_START_SECONDS = 30
CLIP_SECONDS = 60
PLACEHOLDER_SECONDS = 20
AD_SECONDS = 5

WIDTHS = {VideoQuality.Q480P: 854, VideoQuality.Q720P: 1280, VideoQuality.Q1080P: 1920}

# H.264 + AAC + faststart: plays in every browser and starts before fully downloaded
ENCODE_ARGS = [
    "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
]


def run_ffmpeg(args: list[str]) -> None:
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args], check=True)


def find_source(slug: str) -> Optional[Path]:
    return next(SOURCES_DIR.glob(f"{slug}.*"), None)


def cut_from_source(source: Path, quality: VideoQuality, output: Path, start: int) -> None:
    run_ffmpeg([
        "-ss", str(start), "-i", str(source), "-t", str(CLIP_SECONDS),
        "-vf", f"scale=-2:{quality.height}",
        *ENCODE_ARGS, str(output),
    ])


def generate_placeholder(
    quality: VideoQuality, hue: int, output: Path,
    seconds: int = PLACEHOLDER_SECONDS, pattern: str = "testsrc2",
) -> None:
    size = f"{WIDTHS[quality]}x{quality.height}"
    run_ffmpeg([
        "-f", "lavfi", "-i", f"{pattern}=size={size}:rate=25:duration={seconds}",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
        "-vf", f"hue=h={hue}", "-shortest",
        *ENCODE_ARGS, str(output),
    ])


def main() -> None:
    if shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg was not found on PATH")

    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)

    slugs = [slugify(movie[0]) for movie in OPEN_MOVIES] + list(FOOTBALL_CLIPS)

    # Real footage available in media/sources (the ad is not a movie clip)
    available = [s for s in slugs if find_source(s)]
    fallback = 0

    for index, slug in enumerate(slugs):
        source_slug = slug
        if not find_source(slug) and available:
            # No own source: borrow one of the real clips so no title shows a test pattern
            source_slug = available[fallback % len(available)]
            fallback += 1
        source = find_source(source_slug)
        start = 0 if source_slug in FOOTBALL_CLIPS else CLIP_START_SECONDS
        for quality in VideoQuality:
            output = VIDEOS_DIR / f"{slug}_{quality.value}.mp4"
            if source:
                cut_from_source(source, quality, output, start)
            else:
                generate_placeholder(quality, hue=index * 50, output=output)
        print(f"{slug}: {'cut from ' + source.name if source else 'placeholder'}")

    ad_source = find_source("ad")
    if ad_source:
        shutil.copyfile(ad_source, VIDEOS_DIR / "ad.mp4")
        print(f"ad: copied from {ad_source.name}")
    else:
        generate_placeholder(
            VideoQuality.Q720P, hue=0, output=VIDEOS_DIR / "ad.mp4",
            seconds=AD_SECONDS, pattern="smptebars",
        )
        print("ad: placeholder")


if __name__ == "__main__":
    main()