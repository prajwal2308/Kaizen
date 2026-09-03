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

## [0.1.0] - 2026-08-26

### Added
- Project scaffolding: `pyproject.toml`, `src/kaizen` package layout, `kaizen` console entry point.
- `Task` model and JSON-backed `TaskStore` (load/save/next_id) in `src/kaizen/storage.py`.
- CLI commands: `add`, `list` (with `--all`), `done`, `rm` in `src/kaizen/cli.py`.
- Unit tests for storage and CLI (`tests/test_storage.py`, `tests/test_cli.py`).
- GitHub Actions CI running `ruff` and `pytest` on push/PR.
- README, MIT license, and the 90-day build roadmap.
