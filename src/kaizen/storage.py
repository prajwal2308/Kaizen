from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def _default_data_dir() -> Path:
    return Path.home() / ".kaizen"


DATA_DIR = _default_data_dir()
DATA_FILE = "tasks.json"

PRIORITIES = ("low", "med", "high")
DEFAULT_PRIORITY = "med"
_PRIORITY_RANK = {p: i for i, p in enumerate(PRIORITIES)}


def priority_rank(priority: str) -> int:
    """Higher rank sorts first (high, then med, then low)."""
    return -_PRIORITY_RANK[priority]


@dataclass
class Task:
    id: int
    title: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    done: bool = False
    done_at: str | None = None
    priority: str = DEFAULT_PRIORITY

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Task:
        return cls(
            id=data["id"],
            title=data["title"],
            created_at=data.get("created_at", ""),
            done=data.get("done", False),
            done_at=data.get("done_at"),
            priority=data.get("priority", DEFAULT_PRIORITY),
        )


class TaskStore:
    """Persists tasks as JSON in a single file. Not safe for concurrent writers."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or DATA_DIR
        self.path = self.data_dir / DATA_FILE

    def load(self) -> list[Task]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        return [Task.from_dict(item) for item in raw]

    def save(self, tasks: list[Task]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump([t.to_dict() for t in tasks], f, indent=2)

    def next_id(self, tasks: list[Task]) -> int:
        return max((t.id for t in tasks), default=0) + 1
