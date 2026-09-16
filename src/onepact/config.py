from __future__ import annotations

from pathlib import Path

from onepact.storage import DATA_DIR, DEFAULT_PRIORITY, PRIORITIES

CONFIG_FILE = "config.toml"

DEFAULTS: dict[str, str] = {"priority": DEFAULT_PRIORITY}


def _config_path(data_dir: Path | None = None) -> Path:
    return (data_dir or DATA_DIR) / CONFIG_FILE


def _parse_value(raw: str) -> str:
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ('"', "'"):
        return raw[1:-1]
    return raw


def _parse_toml(text: str) -> dict[str, str]:
    """Parses the flat subset of TOML onepact's config actually needs:
    one `key = "value"` pair per line, `#` comments, blank lines. No
    tables, arrays, or multi-line values.
    """
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or "=" not in line:
            continue
        key, _, raw_value = line.partition("=")
        values[key.strip()] = _parse_value(raw_value)
    return values


def load_config(data_dir: Path | None = None) -> dict[str, str]:
    """Loads onepact's config file merged over defaults. A missing file
    is not an error -- it just means the defaults apply.
    """
    config = dict(DEFAULTS)
    path = _config_path(data_dir)
    if path.exists():
        config.update(_parse_toml(path.read_text(encoding="utf-8")))
    if config.get("priority") not in PRIORITIES:
        config["priority"] = DEFAULT_PRIORITY
    return config
