# Changelog

All notable changes to this project are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Changed
- Project renamed from `kaizen` to `onepact`: package, CLI command (`kaizen` → `onepact`), and default data directory (`~/.kaizen` → `~/.onepact`). No behavior change.

### Added
- `kaizen edit <id> <new-title>` command to rename an existing task, with tests.
- `--priority {low,med,high}` on `kaizen add` (default `med`); `list` shows each task's priority and sorts high-priority tasks first.
- `--due YYYY-MM-DD` on `kaizen add`; `list` shows each task's due date and flags past-due, unfinished tasks as `OVERDUE`.
- `--tag <name>` (repeatable) on `kaizen add`; `list` shows each task's tags and `list --tag <name>` filters to tasks carrying that tag.
- `kaizen show <id>` — full detail view of a single task (status, priority, due date with overdue flag, tags, created/completed timestamps).
- `Entry` model and JSON-backed `JournalStore` (load/save/next_id) in `src/onepact/storage.py`, storing journal entries in their own `journal.json`, separate from tasks. First step of Phase 2 (Journaling); no CLI command yet.
- `onepact journal "free text entry"` command that appends a new entry to the journal.
- `onepact journal` with no text argument now opens `$EDITOR` (falling back to `$VISUAL`, then `vi`) for a longer entry; empty entries are discarded rather than saved.
- `onepact journal list` — shows journal entries most recent first (one line each, first line only for multi-line entries), with `--limit N` to cap how many are shown. `journal` is now a command group internally (`add` runs implicitly when the first word after `journal` isn't a known subcommand, so `onepact journal "text"` keeps working unchanged).
- `onepact journal show <id>` — full detail view of a single journal entry (id, timestamp, complete body).
- `--task <id>` on `onepact journal` links a new entry to an existing task; rejects unknown task ids without saving the entry. `journal list` and `journal show` display the linked task when present.
- `onepact journal search <text>` — case-insensitive substring search across journal entry bodies, most recent match first.
- `onepact journal rm <id>` — removes a journal entry after an interactive confirmation prompt (shows the entry's id and first line); `--yes`/`-y` skips the prompt. Declining, or hitting EOF on the prompt, aborts without deleting. This completes Phase 2 (Journaling).
- `onepact find <text>` — case-insensitive substring search across task titles, sorted like `list`; hides completed tasks unless `--all` is passed. Starts Phase 3 (Search, filtering, recurrence). Task line formatting was factored out into a shared `_format_task_line` helper used by both `list` and `find`.
- `list --sort {priority,due,created}` — `priority` (default) keeps the existing high-first ordering, `due` shows the soonest due date first with undated tasks sorted last, and `created` shows the oldest task first.
- `list --overdue` — shorthand filter that shows only past-due, unfinished tasks (the same ones `list` flags `OVERDUE`); combines with `--tag`.
- `--repeat {daily,weekly}` on `add` marks a task as recurring, shown as `[repeat: daily]`/`[repeat: weekly]` in `list`/`find` and as a `Repeat:` line in `show`. This is just the marker for now; auto-creating the next occurrence on completion is a separate, later roadmap item.
- Completing a recurring task now auto-creates its next occurrence: `done` on a task with `repeat` set creates a new task with the same title, priority, tags, and repeat setting, due one day (`daily`) or one week (`weekly`) from the completion date. Non-recurring tasks are unaffected.
- `list --priority <p>` filters to tasks with that priority; combines with `--tag` and `--overdue` since all three are just applied as sequential filters.
- Config file support: `~/.onepact/config.toml` sets defaults, starting with `priority` (used by `add` when `--priority` is omitted; an explicit flag still wins). New `src/onepact/config.py` includes a minimal flat-TOML parser (`key = "value"` pairs, comments, no tables/arrays) rather than adding a dependency or dropping Python 3.10 support, since stdlib `tomllib` needs 3.11+. An invalid `priority` value in the file falls back to `med` rather than erroring.
- `onepact config show` / `onepact config set <key> <value>` — view the current configuration or write a value to `config.toml` from the CLI instead of editing the file by hand. `set` rejects unknown keys and, for `priority`, values outside `low`/`med`/`high`, writing nothing on an invalid call; existing keys in the file are preserved when setting a different one.
- Colorized terminal output: `list`, `find`, `show`, `journal list`, and `journal search` colorize priority, `OVERDUE`, tags, `repeat`, and linked-task markers when stdout is a real terminal. New `src/onepact/color.py` (`should_color()`, `colorize()`) autodetects this — off when piped/redirected, and off on a real terminal too when `NO_COLOR` is set (presence disables it regardless of value, per no-color.org). No `--color`/`--no-color` flag; it's automatic.

### Tests
- Filled gaps in journal command coverage: the explicit `journal add` keyword, an editor-sourced entry linked to a task via `--task`, `journal search` against an empty store, and direct tests of `_read_entry_from_editor` (`$EDITOR`/`$VISUAL` precedence and temp-file cleanup) using a real fake-editor script rather than mocking it away.
- New `tests/test_config.py` covering `load_config`: missing file, quoted/unquoted values, comments, invalid-priority fallback, and unknown keys. Extended with `set_config_value` tests: file creation, overwriting, preserving other keys, and exact written format.
- New `tests/test_color.py` covering `should_color()` (tty/non-tty, `NO_COLOR` set/unset/empty, a stream with no `isatty`) and `colorize()` (single/combined styles, disabled, empty text). CLI tests force color on via a monkeypatched `should_color` to check exact ANSI sequences in `list`/`find`/`show`/`journal list` output, plus one confirming no escape codes appear by default under pytest's non-tty capture.

### Docs
- README: new "Journaling" section documenting `journal` (append, `$EDITOR`, `--task` linking), `journal list` (`--limit`), `journal show`, `journal search`, and `journal rm` (confirmation prompt, `--yes`), plus the `~/.onepact/journal.json` storage location. Every example command was run against a clean data directory to confirm its shown output.
- README Usage section now documents `find`, `list --sort`, `list --overdue`, `list --priority` (and combining filters), and `--repeat` (including completing a recurring task) alongside `list`.
- README "Configuration" section documents `~/.onepact/config.toml`, the `priority` key, and now `config show`/`config set` as the way to view and change it from the CLI.
- New README "Color" section documenting autodetection and `NO_COLOR`.

## [0.1.0] - 2026-08-26

### Added
- Project scaffolding: `pyproject.toml`, `src/kaizen` package layout, `kaizen` console entry point.
- `Task` model and JSON-backed `TaskStore` (load/save/next_id) in `src/kaizen/storage.py`.
- CLI commands: `add`, `list` (with `--all`), `done`, `rm` in `src/kaizen/cli.py`.
- Unit tests for storage and CLI (`tests/test_storage.py`, `tests/test_cli.py`).
- GitHub Actions CI running `ruff` and `pytest` on push/PR.
- README, MIT license, and the 90-day build roadmap.
