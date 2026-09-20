# SQLite schema

Design for roadmap item 31 (Phase 4 — Storage evolution & data safety).
This is the schema `SqliteTaskStore` (item 32) will implement against;
nothing here is wired up yet. `onepact` still runs entirely on the JSON
stores in `src/onepact/storage.py`.

## Goals and constraints

- **Equivalent to the current JSON model.** Every field on `Task` and
  `Entry` (see `src/onepact/storage.py`) has a column here; nothing is
  dropped or renamed without a reason noted below.
- **Same interface, same behavior.** `SqliteTaskStore` and
  `SqliteJournalStore` must implement `load()` / `save()` / `next_id()`
  with results indistinguishable from the JSON stores, so existing CLI
  code and tests don't need to know which backend is active. In
  particular, ids stay small application-assigned integers (`max(id) +
  1`, same as today's `next_id()`) — *not* SQLite's own `AUTOINCREMENT` —
  so a JSON export and a SQLite export of the same data produce the same
  ids. See "ID assignment" below.
- **Round-trippable.** Item 33 (`migrate json-to-sqlite`) and item 36
  (`import`) both need a lossless mapping in both directions between
  this schema and the existing JSON shape.
- **No config table.** `~/.onepact/config.toml` (see `src/onepact/config.py`)
  stays a separate flat file; it's small, human-edited, and has nothing
  to do with task/journal storage.
- **Habits are out of scope.** Phase 5 introduces a `Habit` model; its
  schema will be designed when that phase starts, not guessed at here.

## Tables

```sql
-- One row per task. Mirrors storage.Task field-for-field except `tags`,
-- which is normalized into tags/task_tags below instead of staying an
-- inline list.
CREATE TABLE tasks (
    id         INTEGER PRIMARY KEY,
    title      TEXT    NOT NULL,
    created_at TEXT    NOT NULL,               -- ISO 8601 UTC, e.g. "2026-09-20T00:08:00+00:00"
    done       INTEGER NOT NULL DEFAULT 0
                       CHECK (done IN (0, 1)),  -- SQLite has no native boolean
    done_at    TEXT,                            -- ISO 8601 UTC; NULL until done
    priority   TEXT    NOT NULL DEFAULT 'med'
                       CHECK (priority IN ('low', 'med', 'high')),
    due        TEXT,                            -- "YYYY-MM-DD"; NULL if unset
    repeat     TEXT    CHECK (repeat IS NULL OR repeat IN ('daily', 'weekly'))
);

CREATE INDEX idx_tasks_done     ON tasks (done);
CREATE INDEX idx_tasks_due      ON tasks (due);
CREATE INDEX idx_tasks_priority ON tasks (priority);

-- Distinct tag names, normalized out of Task.tags (a JSON list today).
CREATE TABLE tags (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

-- Many-to-many join between tasks and tags. A task's `tags` list becomes
-- "SELECT name FROM tags JOIN task_tags ... WHERE task_id = ? ORDER BY
-- task_tags.rowid" -- ordered by insertion, matching list order today.
CREATE TABLE task_tags (
    task_id INTEGER NOT NULL REFERENCES tasks (id) ON DELETE CASCADE,
    tag_id  INTEGER NOT NULL REFERENCES tags (id)  ON DELETE CASCADE,
    PRIMARY KEY (task_id, tag_id)
);

CREATE INDEX idx_task_tags_tag_id ON task_tags (tag_id);

-- One row per journal Entry. Named journal_entries, not entries, so it
-- doesn't collide with whatever Phase 5's habit check-ins end up called.
CREATE TABLE journal_entries (
    id         INTEGER PRIMARY KEY,
    body       TEXT    NOT NULL,
    created_at TEXT    NOT NULL,
    task_id    INTEGER REFERENCES tasks (id) ON DELETE SET NULL
);

CREATE INDEX idx_journal_entries_task_id ON journal_entries (task_id);
```

## JSON → SQL field mapping

**`tasks.json` entry → `tasks` row**

| JSON field   | SQL column         | Notes                                    |
|--------------|---------------------|-------------------------------------------|
| `id`         | `tasks.id`          | copied as-is                              |
| `title`      | `tasks.title`        |                                           |
| `created_at` | `tasks.created_at`   |                                           |
| `done`       | `tasks.done`         | `true`/`false` → `1`/`0`                  |
| `done_at`    | `tasks.done_at`      |                                           |
| `priority`   | `tasks.priority`     |                                           |
| `due`        | `tasks.due`          |                                           |
| `tags`       | `tags` + `task_tags` | each string becomes/reuses a `tags` row, linked via `task_tags` in list order |
| `repeat`     | `tasks.repeat`       |                                           |

**`journal.json` entry → `journal_entries` row**

| JSON field  | SQL column                 | Notes |
|-------------|------------------------------|-------|
| `id`        | `journal_entries.id`         |       |
| `body`      | `journal_entries.body`       |       |
| `created_at`| `journal_entries.created_at` |       |
| `task_id`   | `journal_entries.task_id`    | `null` stays `NULL` |

Exporting back the other direction (SQLite → JSON, needed for `export
--format json` in item 35 and for keeping the JSON store as a
back-compat/test backend per item 34) is the same mapping in reverse:
a task's `tags` list is `SELECT name FROM tags JOIN task_tags ...
WHERE task_id = ? ORDER BY task_tags.rowid`.

## ID assignment

SQLite's `INTEGER PRIMARY KEY` is a rowid alias and will happily
auto-assign ids, but `SqliteTaskStore.next_id()` should compute
`max(id) + 1` explicitly (mirroring the JSON stores' current
`next_id()`) rather than relying on that. Two reasons:

1. Deleted rows: SQLite doesn't reuse rowids, but a `rm` followed by an
   `add` should still produce ids that look the same as the JSON
   backend's, so the two backends stay behaviorally identical (item 32's
   requirement).
2. Migration: `migrate json-to-sqlite` needs to insert rows with their
   *existing* JSON ids, not newly generated ones — `INSERT INTO tasks
   (id, ...) VALUES (?, ...)` with the id supplied explicitly.

## Schema versioning

Use SQLite's built-in `PRAGMA user_version` (an integer stored in the
database file header) to track schema revisions, rather than adding a
bespoke `schema_meta` table. `SqliteTaskStore` sets it to `1` on first
create; a later schema change bumps it and checks it on open to decide
whether a migration step is needed.

## Explicitly deferred

- Full-text search over journal bodies (the current `journal search`
  is a plain substring scan over JSON; an FTS5 virtual table would be a
  reasonable future upgrade once SQLite is the default backend, but
  isn't needed for parity with today's behavior).
- A `habits` table (Phase 5).
- Storing `config.toml` in SQLite (deliberately staying a separate file).
