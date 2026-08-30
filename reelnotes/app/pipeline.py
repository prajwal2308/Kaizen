"""url in, note out. The whole product is this function."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from . import extract as extract_mod
from . import media as media_mod
from . import notify, transcribe
from .config import Settings
from .store import Store

log = logging.getLogger(__name__)


def process(note_id: str, url: str, settings: Settings, store: Store) -> None:
    """Run one reel end to end. Never raises: failures are recorded and pushed."""
    try:
        with tempfile.TemporaryDirectory(prefix="reelnotes-") as tmp:
            workdir = Path(tmp)

            item = media_mod.fetch(
                url,
                workdir,
                cookies_file=settings.cookies_file,
                frame_count=settings.frame_count,
                max_duration_seconds=settings.max_duration_seconds,
            )
            text = transcribe.transcribe(
                item.audio_path,
                backend=settings.asr_backend,
                model_size=settings.whisper_model,
            )
            note = extract_mod.extract(
                transcript=text,
                frames=item.frames,
                model=settings.model,
                source_title=item.title,
                uploader=item.uploader,
                description=item.description,
            )
            # The middle frame is the most representative one; the samples are
            # already taken from inside the clip.
            thumbnail = item.frames[len(item.frames) // 2] if item.frames else None

        store.save_note(
            note_id,
            note,
            transcript=text,
            source_title=item.title,
            uploader=item.uploader,
            duration=item.duration,
            thumbnail=thumbnail,
        )

        if settings.push_enabled:
            base = settings.public_base_url
            click = f"{base}/notes/{note_id}" if base else None
            notify.push_note(
                note,
                server=settings.ntfy_server,
                topic=settings.ntfy_topic,
                click_url=click,
            )

    except Exception as exc:
        log.exception("Failed to process %s", url)
        store.mark_failed(note_id, str(exc))
        if settings.push_enabled:
            notify.push_failure(
                url, str(exc), server=settings.ntfy_server, topic=settings.ntfy_topic
            )
