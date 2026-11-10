"""Launches `$EDITOR` (falling back to `$VISUAL`, then `vi`) against a
temporary file and returns what was written to it. Shared by the
no-args `onepact journal` command and `onepact ui`'s interactive
Journal panel, so the editor-launch mechanics (env var fallback,
tempfile lifecycle, leaving `subprocess.CalledProcessError`/`OSError`
for the caller to handle) aren't duplicated in both places.
"""

from __future__ import annotations

import os
import subprocess
import tempfile


def read_entry_from_editor(initial: str = "") -> str:
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vi"
    fd, tmp_path = tempfile.mkstemp(suffix=".md", prefix="onepact-journal-")
    if initial:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(initial)
    else:
        os.close(fd)
    try:
        subprocess.run([editor, tmp_path], check=True)
        with open(tmp_path, encoding="utf-8") as f:
            return f.read()
    finally:
        os.remove(tmp_path)
