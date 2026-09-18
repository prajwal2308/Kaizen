from __future__ import annotations

import os
import sys
from typing import TextIO

RESET = "\033[0m"

_CODES = {
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "bold": "1",
    "dim": "2",
}


def should_color(stream: TextIO | None = None) -> bool:
    """True if output should be colorized: no NO_COLOR env var (its
    presence disables color regardless of value, per no-color.org) and
    the target stream is a real terminal.
    """
    if "NO_COLOR" in os.environ:
        return False
    stream = stream if stream is not None else sys.stdout
    isatty = getattr(stream, "isatty", None)
    return bool(isatty and isatty())


def colorize(text: str, *styles: str, enabled: bool) -> str:
    if not enabled or not text:
        return text
    codes = ";".join(_CODES[s] for s in styles)
    return f"\033[{codes}m{text}{RESET}"
