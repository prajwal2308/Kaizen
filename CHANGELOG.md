# Changelog

All notable changes to this project are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## [0.1.0] - 2026-08-26

### Added
- Project scaffolding: `pyproject.toml`, `src/kaizen` package layout, `kaizen` console entry point.
- `Task` model and JSON-backed `TaskStore` (load/save/next_id) in `src/kaizen/storage.py`.
- CLI commands: `add`, `list` (with `--all`), `done`, `rm` in `src/kaizen/cli.py`.
- Unit tests for storage and CLI (`tests/test_storage.py`, `tests/test_cli.py`).
- GitHub Actions CI running `ruff` and `pytest` on push/PR.
- README, MIT license, and the 90-day build roadmap.
