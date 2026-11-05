from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


def _default_data_dir() -> Path:
    return Path.home() / ".onepact"


DATA_DIR = _default_data_dir()
DATA_FILE = "tasks.json"
JOURNAL_FILE = "journal.json"
HABIT_FILE = "habits.json"

PRIORITIES = ("low", "med", "high")
DEFAULT_PRIORITY = "med"
_PRIORITY_RANK = {p: i for i, p in enumerate(PRIORITIES)}

REPEATS = ("daily", "weekly")


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
    due: str | None = None
    tags: list[str] = field(default_factory=list)
    repeat: str | None = None

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
            due=data.get("due"),
            tags=list(data.get("tags", [])),
            repeat=data.get("repeat"),
        )


def is_overdue(task: Task, today: str) -> bool:
    """A task is overdue if it has a due date in the past and isn't done yet.

    `today` is an ISO `YYYY-MM-DD` string; ISO dates compare correctly as strings.
    """
    return task.due is not None and not task.done and task.due < today


_REPEAT_DELTA = {"daily": timedelta(days=1), "weekly": timedelta(days=7)}


def complete_task(tasks: list[Task], task_id: int, today: date) -> tuple[Task, Task | None] | None:
    """Marks the task with this id done (setting `done_at` to the current
    moment) and, if it's recurring, appends the next occurrence to
    `tasks` in place -- same title, priority, tags, and repeat setting,
    due one day (`daily`) or one week (`weekly`) from `today`. Returns
    `(completed_task, next_occurrence_or_None)`, or `None` if no task
    with this id exists. Shared by `cmd_done` and the interactive task
    panel in `onepact ui` so this isn't duplicated in two places.
    """
    for t in tasks:
        if t.id == task_id:
            t.done = True
            t.done_at = datetime.now(timezone.utc).isoformat()
            next_task = None
            if t.repeat:
                next_due = (today + _REPEAT_DELTA[t.repeat]).isoformat()
                next_task = Task(
                    id=max((x.id for x in tasks), default=0) + 1,
                    title=t.title,
                    priority=t.priority,
                    due=next_due,
                    tags=list(t.tags),
                    repeat=t.repeat,
                )
                tasks.append(next_task)
            return t, next_task
    return None


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


@dataclass
class Entry:
    id: int
    body: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    task_id: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Entry:
        return cls(
            id=data["id"],
            body=data["body"],
            created_at=data.get("created_at", ""),
            task_id=data.get("task_id"),
        )


class JournalStore:
    """Persists journal entries as JSON in their own file, separate from tasks."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or DATA_DIR
        self.path = self.data_dir / JOURNAL_FILE

    def load(self) -> list[Entry]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        return [Entry.from_dict(item) for item in raw]

    def save(self, entries: list[Entry]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in entries], f, indent=2)

    def next_id(self, entries: list[Entry]) -> int:
        return max((e.id for e in entries), default=0) + 1


@dataclass
class Habit:
    name: str
    frequency: str
    streak: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_checked: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Habit:
        return cls(
            name=data["name"],
            frequency=data.get("frequency", "daily"),
            streak=data.get("streak", 0),
            created_at=data.get("created_at", ""),
            last_checked=data.get("last_checked"),
        )


_STREAK_GRACE_DAYS = {"daily": 1, "weekly": 7}


def check_in_habit(habit: Habit, today: date) -> str:
    """Marks `habit` checked in for `today`, mutating it in place.
    Continues the streak if the gap since `last_checked` is within the
    habit's frequency's grace period, resets it to 1 otherwise -- same
    rule either way, just whether it's a break or a continuation.
    Returns `"already"` if the habit was already checked in today
    (nothing changes), `"missed"` if a check-in was overdue (streak
    reset to 1), or `"ok"` for a normal increment. Shared by
    `cmd_habit_check` and the interactive habit panel in `onepact ui`
    so the streak rules aren't duplicated in two places.
    """
    today_str = today.isoformat()
    if habit.last_checked == today_str:
        return "already"
    missed = False
    if habit.last_checked is not None:
        gap_days = (today - date.fromisoformat(habit.last_checked)).days
        if gap_days > _STREAK_GRACE_DAYS[habit.frequency]:
            habit.streak = 0
            missed = True
    habit.streak += 1
    habit.last_checked = today_str
    return "missed" if missed else "ok"


class HabitStore:
    """Persists habits as JSON in their own file, separate from tasks and
    journal entries. Habits are identified by name rather than an int id,
    since every roadmapped habit command (`add`, `check`, `list`) refers to
    one by name.
    """

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or DATA_DIR
        self.path = self.data_dir / HABIT_FILE

    def load(self) -> list[Habit]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        return [Habit.from_dict(item) for item in raw]

    def save(self, habits: list[Habit]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump([h.to_dict() for h in habits], f, indent=2)
