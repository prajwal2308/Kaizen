"""Fetch the reel and render it down to what the model needs: audio + frames.

This is the fragile half of the system. Meta does not offer an API that returns
a third-party reel's media, so this uses yt-dlp, which means it will break
periodically and needs a logged-in cookie jar for most URLs. Everything here is
written to fail loudly with a message that says which half broke.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


class MediaError(RuntimeError):
    """Raised when the reel could not be fetched or decoded."""


@dataclass
class Media:
    audio_path: Path
    frames: list[bytes] = field(default_factory=list)
    title: str | None = None
    description: str | None = None
    uploader: str | None = None
    duration: float | None = None


def fetch(url: str, workdir: Path, *, cookies_file: str | None, frame_count: int,
          max_duration_seconds: int) -> Media:
    if shutil.which("ffmpeg") is None:
        raise MediaError("ffmpeg is not installed or not on PATH.")

    info, video_path = _download(url, workdir, cookies_file)

    duration = info.get("duration")
    if duration and duration > max_duration_seconds:
        raise MediaError(
            f"Reel is {duration:.0f}s, longer than the {max_duration_seconds}s limit."
        )

    audio_path = workdir / "audio.wav"
    _run(
        # 16 kHz mono is what Whisper wants; anything richer is thrown away.
        ["ffmpeg", "-nostdin", "-y", "-i", str(video_path),
         "-vn", "-ac", "1", "-ar", "16000", "-f", "wav", str(audio_path)],
        "extract audio",
    )

    frames = _extract_frames(video_path, workdir, duration, frame_count)

    return Media(
        audio_path=audio_path,
        frames=frames,
        title=info.get("title"),
        description=info.get("description"),
        uploader=info.get("uploader") or info.get("channel"),
        duration=duration,
    )


def _download(url: str, workdir: Path, cookies_file: str | None) -> tuple[dict, Path]:
    try:
        from yt_dlp import YoutubeDL
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise MediaError("yt-dlp is not installed.") from exc

    opts: dict = {
        "outtmpl": str(workdir / "source.%(ext)s"),
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 3,
    }
    if cookies_file:
        opts["cookiefile"] = cookies_file

    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as exc:
        raise MediaError(
            f"Could not fetch the reel ({exc}). Most Instagram and Facebook URLs need a "
            "logged-in cookie jar — see YTDLP_COOKIES_FILE in the README."
        ) from exc

    candidates = sorted(workdir.glob("source.*"), key=lambda p: p.stat().st_size, reverse=True)
    if not candidates:
        raise MediaError("yt-dlp reported success but wrote no file.")
    return info, candidates[0]


def _extract_frames(video: Path, workdir: Path, duration: float | None, count: int) -> list[bytes]:
    """Evenly spaced stills.

    Reels routinely put the actual numbers on screen and never say them aloud,
    so the frames are not decoration — without them the transcript alone loses
    the part you wanted.
    """
    if count <= 0:
        return []
    span = duration or 30.0
    # Sample strictly inside the clip; the first and last frames are usually a
    # title card and a "follow for more".
    offsets = [span * (i + 1) / (count + 1) for i in range(count)]

    frames: list[bytes] = []
    for index, offset in enumerate(offsets):
        out = workdir / f"frame_{index}.jpg"
        try:
            _run(
                ["ffmpeg", "-nostdin", "-y", "-ss", f"{offset:.2f}", "-i", str(video),
                 "-frames:v", "1", "-vf", "scale=768:-2", "-q:v", "4", str(out)],
                f"extract frame at {offset:.1f}s",
            )
        except MediaError:
            continue  # A missing frame is survivable; a missing transcript is not.
        if out.exists():
            frames.append(out.read_bytes())
    return frames


def _run(cmd: list[str], what: str) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        tail = (result.stderr or "").strip().splitlines()[-3:]
        raise MediaError(f"ffmpeg failed to {what}: {' '.join(tail)}")
