# Roadmap

This is the single source of truth for what to build next. It's a flat,
ordered checklist — each item is meant to be small enough to design,
implement, test, and ship in one sitting.

**Working rule:** always do the *first unchecked item*, in order. Don't skip
ahead, don't batch multiple items in one commit. Keep the tool working and
`pytest -q` green after every single item. When an item is done, check it off
here and add a dated entry under `[Unreleased]` in `CHANGELOG.md` in the same
commit.

If every item below is checked, don't stop: read through the codebase for a
genuinely useful next phase (informed by what actually got built), append a
new batch of items in this same format, and start on the first one.

## Phase 1 — Foundations

- [x] 1. Project scaffolding: `pyproject.toml`, `src/kaizen` layout, console entry point
- [x] 2. `Task` dataclass + JSON `TaskStore` (load/save/next_id)
- [x] 3. CLI: `add`, `list` (+ `--all`), `done`, `rm`
- [x] 4. Unit tests for storage and CLI
- [x] 5. GitHub Actions CI (ruff + pytest)
- [x] 6. `kaizen edit <id> <new-title>` command + tests
- [x] 7. Priorities: `--priority {low,med,high}` on `add`, shown in `list`, sortable
- [ ] 8. Due dates: `--due YYYY-MM-DD` on `add`; `list` shows overdue items distinctly
- [ ] 9. Tags: `--tag work --tag home` (repeatable) on `add`; `list --tag work` filters
- [ ] 10. `kaizen show <id>` — full detail view of a single task

## Phase 2 — Journaling

- [ ] 11. `Entry` model (id, timestamp, body) + `JournalStore` (separate JSON file)
- [ ] 12. `kaizen journal "free text entry"` appends an entry
- [ ] 13. `kaizen journal` with no args opens `$EDITOR` for a longer entry
- [ ] 14. `kaizen journal list` — most recent entries first, with `--limit`
- [ ] 15. `kaizen journal show <id>`
- [ ] 16. Link a journal entry to a task: `--task <id>` on `journal`
- [ ] 17. `kaizen journal search <text>` — substring search across entries
- [ ] 18. Tests for all journal commands
- [ ] 19. README section documenting journaling workflow
- [ ] 20. `kaizen journal rm <id>` with confirmation prompt (skippable via `--yes`)

## Phase 3 — Search, filtering, recurrence

- [ ] 21. `kaizen find <text>` — search task titles (case-insensitive substring)
- [ ] 22. `list --sort {priority,due,created}` 
- [ ] 23. `list --overdue` shorthand filter
- [ ] 24. Recurring tasks: `--repeat {daily,weekly}` on `add`
- [ ] 25. Completing a recurring task auto-creates the next occurrence
- [ ] 26. `kaizen list --tag <t> --priority <p>` combinable filters
- [ ] 27. Config file support: `~/.kaizen/config.toml` for defaults (e.g. default priority)
- [ ] 28. `kaizen config show` / `kaizen config set <key> <value>`
- [ ] 29. Colorized terminal output (respect `NO_COLOR` / non-tty)
- [ ] 30. Tests for sorting, filtering, recurrence, and config

## Phase 4 — Storage evolution & data safety

- [ ] 31. Design a SQLite schema equivalent to the current JSON model
- [ ] 32. `SqliteTaskStore` implementing the same interface as `TaskStore`
- [ ] 33. One-time migration command: `kaizen migrate json-to-sqlite`
- [ ] 34. Switch default backend to SQLite behind a storage interface; keep JSON store for tests/back-compat
- [ ] 35. `kaizen export --format json` and `kaizen export --format csv`
- [ ] 36. `kaizen import <file>` (round-trips with export)
- [ ] 37. Automatic backup of the data file before destructive operations (`rm`, `migrate`)
- [ ] 38. `kaizen undo` — revert the last destructive action (single-level undo log)
- [ ] 39. Data integrity tests: migration round-trip, export/import round-trip
- [ ] 40. Document data locations and backup strategy in README

## Phase 5 — Habits & daily review

- [ ] 41. `Habit` model (name, frequency, streak) + `HabitStore`
- [ ] 42. `kaizen habit add <name> --daily|--weekly`
- [ ] 43. `kaizen habit check <name>` — mark today's occurrence done
- [ ] 44. `kaizen habit list` — shows current streak per habit
- [ ] 45. Streak-breaking logic: missed day resets streak, tested with fixed clock
- [ ] 46. `kaizen review` — a single daily-review view: overdue tasks, today's habits, last journal entry
- [ ] 47. `kaizen review --since yesterday` for a quick catch-up view
- [ ] 48. Stats: `kaizen stats` — tasks completed this week, current streaks, journal cadence
- [ ] 49. Tests for habits and review/stats commands
- [ ] 50. README section documenting habits + daily review workflow

## Phase 6 — Polish & release

- [ ] 51. Consistent error handling: exit codes, no raw tracebacks on user errors
- [ ] 52. `kaizen --version`
- [ ] 53. Shell completion script (bash/zsh) generation
- [ ] 54. Man-page-style `--help` polish for every subcommand (examples in help text)
- [ ] 55. Type-check with `mypy` (or `pyright`) added to CI
- [ ] 56. Packaging: verify `pip install .` works in a clean venv from a tagged release
- [ ] 57. `CONTRIBUTING.md` with dev setup, test, and lint instructions
- [ ] 58. Expand CI matrix (3.10–3.13) and add a coverage report step
- [ ] 59. Tag and publish `v1.0.0` (CHANGELOG entry, GitHub release notes)
- [ ] 60. Post-1.0: revisit this roadmap, write Phase 7 based on real usage

---

When you reach the end of this list, don't leave it empty: propose the next
phase yourself, in this same format, based on what would make the tool
genuinely more useful — not filler.
