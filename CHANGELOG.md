# Changelog

All notable changes to this project are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- `kaizen edit <id> <new-title>` command to rename an existing task, with tests.
- `--priority {low,med,high}` on `kaizen add` (default `med`); `list` shows each task's priority and sorts high-priority tasks first.
- `--due YYYY-MM-DD` on `kaizen add`; `list` shows each task's due date and flags past-due, unfinished tasks as `OVERDUE`.
- `--tag <name>` (repeatable) on `kaizen add`; `list` shows each task's tags and `list --tag <name>` filters to tasks carrying that tag.
- `kaizen show <id>` — full detail view of a single task (status, priority, due date with overdue flag, tags, created/completed timestamps).

## [0.1.0] - 2026-08-26

### Added
- Project scaffolding: `pyproject.toml`, `src/kaizen` package layout, `kaizen` console entry point.
- `Task` model and JSON-backed `TaskStore` (load/save/next_id) in `src/kaizen/storage.py`.
- CLI commands: `add`, `list` (with `--all`), `done`, `rm` in `src/kaizen/cli.py`.
- Unit tests for storage and CLI (`tests/test_storage.py`, `tests/test_cli.py`).
- GitHub Actions CI running `ruff` and `pytest` on push/PR.
- README, MIT license, and the 90-day build roadmap.
