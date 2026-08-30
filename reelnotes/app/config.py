"""Runtime configuration, read once from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Everything the service needs to run, resolved from env vars."""

    # Shared secret the iOS Shortcut sends as X-API-Key. The service refuses to
    # start without it: this endpoint downloads and transcribes whatever URL it
    # is handed, so an open one is somebody else's free compute.
    api_key: str
    db_path: str

    model: str
    asr_backend: str
    whisper_model: str

    ntfy_server: str
    ntfy_topic: str | None
    public_base_url: str | None

    # yt-dlp needs a logged-in session for most Instagram/Facebook URLs.
    cookies_file: str | None
    frame_count: int
    max_duration_seconds: int

    @property
    def push_enabled(self) -> bool:
        return bool(self.ntfy_topic)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    api_key = os.environ.get("REELNOTES_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "REELNOTES_API_KEY is not set. Generate one with "
            "`python -c 'import secrets; print(secrets.token_urlsafe(32))'` and set it "
            "on both the server and the iOS Shortcut."
        )
    return Settings(
        api_key=api_key,
        db_path=os.environ.get("REELNOTES_DB", "reelnotes.sqlite3"),
        model=os.environ.get("REELNOTES_MODEL", "claude-opus-5"),
        asr_backend=os.environ.get("REELNOTES_ASR", "faster-whisper"),
        whisper_model=os.environ.get("REELNOTES_WHISPER_MODEL", "small"),
        ntfy_server=os.environ.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/"),
        ntfy_topic=os.environ.get("NTFY_TOPIC") or None,
        public_base_url=(os.environ.get("PUBLIC_BASE_URL") or "").rstrip("/") or None,
        cookies_file=os.environ.get("YTDLP_COOKIES_FILE") or None,
        frame_count=int(os.environ.get("REELNOTES_FRAMES", "4")),
        max_duration_seconds=int(os.environ.get("REELNOTES_MAX_DURATION", "900")),
    )
