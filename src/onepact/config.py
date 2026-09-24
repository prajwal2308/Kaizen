from __future__ import annotations

from pathlib import Path

from onepact.storage import DATA_DIR, DEFAULT_PRIORITY, PRIORITIES

CONFIG_FILE = "config.toml"

BACKENDS = ("sqlite", "json")
DEFAULT_BACKEND = "sqlite"

DEFAULTS: dict[str, str] = {"priority": DEFAULT_PRIORITY, "backend": DEFAULT_BACKEND}
SUPPORTED_KEYS = tuple(DEFAULTS)


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
    if config.get("backend") not in BACKENDS:
        config["backend"] = DEFAULT_BACKEND
    return config


def _read_raw(data_dir: Path | None = None) -> dict[str, str]:
    """Like load_config, but only what's actually in the file -- no
    defaults merged in. Used by set_config_value so writing one key
    doesn't bake in every default as an explicit file entry.
    """
    path = _config_path(data_dir)
    if not path.exists():
        return {}
    return _parse_toml(path.read_text(encoding="utf-8"))


def _write_raw(values: dict[str, str], data_dir: Path | None = None) -> None:
    path = _config_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f'{key} = "{value}"' for key, value in sorted(values.items())]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def set_config_value(key: str, value: str, data_dir: Path | None = None) -> None:
    raw = _read_raw(data_dir)
    raw[key] = value
    _write_raw(raw, data_dir)
