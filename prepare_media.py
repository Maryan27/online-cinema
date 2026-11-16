"""Prepare demo video files in three qualities plus the ad clip.

For every open-movie clip used in seed.py:
  * if media/sources/<slug>.<ext> exists, a 60-second fragment is cut from it;
  * otherwise a colourful test-pattern video is generated as a placeholder.

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
from seed import OPEN_MOVIES, slugify

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


def cut_from_source(source: Path, quality: VideoQuality, output: Path) -> None:
    run_ffmpeg([
        "-ss", str(CLIP_START_SECONDS), "-i", str(source), "-t", str(CLIP_SECONDS),
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

    for index, movie in enumerate(OPEN_MOVIES):
        slug = slugify(movie[0])
        source = find_source(slug)
        for quality in VideoQuality:
            output = VIDEOS_DIR / f"{slug}_{quality.value}.mp4"
            if source:
                cut_from_source(source, quality, output)
            else:
                generate_placeholder(quality, hue=index * 50, output=output)
        print(f"{slug}: {'cut from ' + source.name if source else 'placeholder'}")

    generate_placeholder(
        VideoQuality.Q720P, hue=0, output=VIDEOS_DIR / "ad.mp4",
        seconds=AD_SECONDS, pattern="smptebars",
    )
    print("ad: placeholder")


if __name__ == "__main__":
    main()