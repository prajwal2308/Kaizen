from __future__ import annotations

import sqlite3
from pathlib import Path

from onepact.storage import DATA_DIR, Task

DB_FILE = "onepact.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id         INTEGER PRIMARY KEY,
    title      TEXT    NOT NULL,
    created_at TEXT    NOT NULL,
    done       INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
    done_at    TEXT,
    priority   TEXT    NOT NULL DEFAULT 'med' CHECK (priority IN ('low', 'med', 'high')),
    due        TEXT,
    repeat     TEXT CHECK (repeat IS NULL OR repeat IN ('daily', 'weekly'))
);

CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks (done);
CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks (due);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks (priority);

CREATE TABLE IF NOT EXISTS tags (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS task_tags (
    task_id INTEGER NOT NULL REFERENCES tasks (id) ON DELETE CASCADE,
    tag_id  INTEGER NOT NULL REFERENCES tags (id)  ON DELETE CASCADE,
    PRIMARY KEY (task_id, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_task_tags_tag_id ON task_tags (tag_id);
"""


class SqliteTaskStore:
    """Persists tasks in a SQLite database, per SCHEMA.md. Implements the
    same load/save/next_id interface as storage.TaskStore -- a drop-in
    replacement, not a subclass -- so callers don't need to know which
    backend is active (roadmap items 32/34). Not wired up as the default
    yet; TaskStore (JSON) still is.
    """

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or DATA_DIR
        self.path = self.data_dir / DB_FILE

    def _connect(self) -> sqlite3.Connection:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.executescript(_SCHEMA)
        conn.execute("PRAGMA user_version = 1;")
        return conn

    def load(self) -> list[Task]:
        if not self.path.exists():
            return []
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT id, title, created_at, done, done_at, priority, due, repeat "
                "FROM tasks ORDER BY id"
            ).fetchall()
            tasks = []
            for row in rows:
                task_id = row[0]
                tags = [
                    name
                    for (name,) in conn.execute(
                        "SELECT tags.name FROM tags "
                        "JOIN task_tags ON tags.id = task_tags.tag_id "
                        "WHERE task_tags.task_id = ? ORDER BY task_tags.rowid",
                        (task_id,),
                    )
                ]
                tasks.append(
                    Task(
                        id=row[0],
                        title=row[1],
                        created_at=row[2],
                        done=bool(row[3]),
                        done_at=row[4],
                        priority=row[5],
                        due=row[6],
                        tags=tags,
                        repeat=row[7],
                    )
                )
            return tasks
        finally:
            conn.close()

    def save(self, tasks: list[Task]) -> None:
        conn = self._connect()
        try:
            conn.execute("DELETE FROM task_tags")
            conn.execute("DELETE FROM tasks")
            for t in tasks:
                conn.execute(
                    "INSERT INTO tasks "
                    "(id, title, created_at, done, done_at, priority, due, repeat) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        t.id,
                        t.title,
                        t.created_at,
                        int(t.done),
                        t.done_at,
                        t.priority,
                        t.due,
                        t.repeat,
                    ),
                )
                for name in t.tags:
                    conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,))
                    (tag_id,) = conn.execute(
                        "SELECT id FROM tags WHERE name = ?", (name,)
                    ).fetchone()
                    conn.execute(
                        "INSERT INTO task_tags (task_id, tag_id) VALUES (?, ?)",
                        (t.id, tag_id),
                    )
            conn.commit()
        finally:
            conn.close()

    def next_id(self, tasks: list[Task]) -> int:
        return max((t.id for t in tasks), default=0) + 1
