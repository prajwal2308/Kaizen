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

### Tests
- Filled gaps in journal command coverage: the explicit `journal add` keyword, an editor-sourced entry linked to a task via `--task`, `journal search` against an empty store, and direct tests of `_read_entry_from_editor` (`$EDITOR`/`$VISUAL` precedence and temp-file cleanup) using a real fake-editor script rather than mocking it away.

### Docs
- README: new "Journaling" section documenting `journal` (append, `$EDITOR`, `--task` linking), `journal list` (`--limit`), `journal show`, `journal search`, and `journal rm` (confirmation prompt, `--yes`), plus the `~/.onepact/journal.json` storage location. Every example command was run against a clean data directory to confirm its shown output.

## [0.1.0] - 2026-08-26

### Added
- Project scaffolding: `pyproject.toml`, `src/kaizen` package layout, `kaizen` console entry point.
- `Task` model and JSON-backed `TaskStore` (load/save/next_id) in `src/kaizen/storage.py`.
- CLI commands: `add`, `list` (with `--all`), `done`, `rm` in `src/kaizen/cli.py`.
- Unit tests for storage and CLI (`tests/test_storage.py`, `tests/test_cli.py`).
- GitHub Actions CI running `ruff` and `pytest` on push/PR.
- README, MIT license, and the 90-day build roadmap.
