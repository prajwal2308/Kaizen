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

- [x] 1. Project scaffolding: `pyproject.toml`, `src/onepact` layout, console entry point
- [x] 2. `Task` dataclass + JSON `TaskStore` (load/save/next_id)
- [x] 3. CLI: `add`, `list` (+ `--all`), `done`, `rm`
- [x] 4. Unit tests for storage and CLI
- [x] 5. GitHub Actions CI (ruff + pytest)
- [x] 6. `onepact edit <id> <new-title>` command + tests
- [x] 7. Priorities: `--priority {low,med,high}` on `add`, shown in `list`, sortable
- [x] 8. Due dates: `--due YYYY-MM-DD` on `add`; `list` shows overdue items distinctly
- [x] 9. Tags: `--tag work --tag home` (repeatable) on `add`; `list --tag work` filters
- [x] 10. `onepact show <id>` — full detail view of a single task

## Phase 2 — Journaling

- [x] 11. `Entry` model (id, timestamp, body) + `JournalStore` (separate JSON file)
- [x] 12. `onepact journal "free text entry"` appends an entry
- [x] 13. `onepact journal` with no args opens `$EDITOR` for a longer entry
- [x] 14. `onepact journal list` — most recent entries first, with `--limit`
- [x] 15. `onepact journal show <id>`
- [x] 16. Link a journal entry to a task: `--task <id>` on `journal`
- [x] 17. `onepact journal search <text>` — substring search across entries
- [x] 18. Tests for all journal commands
- [x] 19. README section documenting journaling workflow
- [x] 20. `onepact journal rm <id>` with confirmation prompt (skippable via `--yes`)

## Phase 3 — Search, filtering, recurrence

- [x] 21. `onepact find <text>` — search task titles (case-insensitive substring)
- [x] 22. `list --sort {priority,due,created}` 
- [x] 23. `list --overdue` shorthand filter
- [x] 24. Recurring tasks: `--repeat {daily,weekly}` on `add`
- [x] 25. Completing a recurring task auto-creates the next occurrence
- [x] 26. `onepact list --tag <t> --priority <p>` combinable filters
- [x] 27. Config file support: `~/.onepact/config.toml` for defaults (e.g. default priority)
- [x] 28. `onepact config show` / `onepact config set <key> <value>`
- [x] 29. Colorized terminal output (respect `NO_COLOR` / non-tty)
- [x] 30. Tests for sorting, filtering, recurrence, and config

## Phase 4 — Storage evolution & data safety

- [x] 31. Design a SQLite schema equivalent to the current JSON model
- [x] 32. `SqliteTaskStore` implementing the same interface as `TaskStore`
- [x] 33. One-time migration command: `onepact migrate json-to-sqlite`
- [x] 34. Switch default backend to SQLite behind a storage interface; keep JSON store for tests/back-compat
- [x] 35. `onepact export --format json` and `onepact export --format csv`
- [x] 36. `onepact import <file>` (round-trips with export)
- [x] 37. Automatic backup of the data file before destructive operations (`rm`, `migrate`)
- [x] 38. `onepact undo` — revert the last destructive action (single-level undo log)
- [x] 39. Data integrity tests: migration round-trip, export/import round-trip
- [x] 40. Document data locations and backup strategy in README

## Phase 5 — Habits & daily review

- [x] 41. `Habit` model (name, frequency, streak) + `HabitStore`
- [x] 42. `onepact habit add <name> --daily|--weekly`
- [x] 43. `onepact habit check <name>` — mark today's occurrence done
- [x] 44. `onepact habit list` — shows current streak per habit
- [x] 45. Streak-breaking logic: missed day resets streak, tested with fixed clock
- [x] 46. `onepact review` — a single daily-review view: overdue tasks, today's habits, last journal entry
- [x] 47. `onepact review --since yesterday` for a quick catch-up view
- [x] 48. Stats: `onepact stats` — tasks completed this week, current streaks, journal cadence
- [x] 49. Tests for habits and review/stats commands
- [x] 50. README section documenting habits + daily review workflow

## Phase 6 — Polish & release

- [x] 51. Consistent error handling: exit codes, no raw tracebacks on user errors
- [x] 52. `onepact --version`
- [x] 53. Shell completion script (bash/zsh) generation
- [x] 54. Man-page-style `--help` polish for every subcommand (examples in help text)
- [x] 55. Type-check with `mypy` (or `pyright`) added to CI
- [x] 56. Packaging: verify `pip install .` works in a clean venv from a tagged release
- [x] 57. `CONTRIBUTING.md` with dev setup, test, and lint instructions
- [x] 58. Expand CI matrix (3.10–3.13) and add a coverage report step
- [ ] 59. Tag and publish `v1.0.0` (CHANGELOG entry, GitHub release notes)
- [x] 60. Post-1.0: revisit this roadmap, write Phase 7 based on real usage

## Phase 7 — Living with onepact

Phases 1-6 built the feature set; this phase is about the friction that
only shows up after actually using it day to day. Each of these is a
real gap found by reading the current code against what a daily user
would hit, not a hypothetical:

- [x] 61. `onepact habit rm <name>` — habits can be added but never removed; a habit you stopped doing (or mistyped) is stuck forever. Same confirm/`--yes` pattern as `journal rm`.
- [x] 62. `onepact habit edit <name> <new-name>` — rename a habit without losing its streak history. No habit command currently touches an existing habit after creation.
- [x] 63. `onepact tags` — list every tag currently in use across tasks, with a count per tag. `list --tag <t>` already filters by tag, but finding out what tags exist in the first place means reading raw data.
- [x] 64. `--due today` / `--due tomorrow` shorthand on `add` and `edit`, resolved to real dates at write time. Not a general natural-language date parser — just the two inputs that are actually typed daily instead of `YYYY-MM-DD`.
- [x] 65. `onepact journal edit <id>` — fix a journal entry's body in place (reuses the existing `$EDITOR` flow from the no-args `journal` command) without losing its id, timestamp, or linked task. Currently the only way to correct a typo is `rm` + re-add, which loses all three.
- [ ] 66. `onepact archive` — move completed, non-recurring tasks older than a configurable number of days out of the active task file into a separate archive file. `list`/`find`/`show` only ever grow; there's no way to declutter without permanently losing history via `rm`.
- [ ] 67. `onepact stats --weekly` — compare this week's numbers (tasks completed, journal entries) against last week's. `stats` currently reports one rolling-7-day snapshot with nothing to compare it to, so trends aren't visible.
- [ ] 68. README section documenting the above (habit maintenance, tag overview, due-date shorthand, journal correction, archiving, stats trends).

## Phase 8 — Terminal UI

Everything so far is single-shot commands: run one, get one screen of
output, back to the shell prompt. This phase adds an optional
full-screen interactive view on top of the same stores, for anyone who
wants a dashboard instead of memorized commands. Built on Python's
built-in `curses` rather than a third-party TUI library, matching the
project's existing zero-runtime-dependency stance. Every CLI command
keeps working exactly as it does today — this is additive, not a
replacement.

- [ ] 69. `onepact ui` — a new top-level command that launches a full-screen `curses` dashboard. First pass is read-only: a task panel (same info as `list`), a habit panel (name/frequency/streak), and a recent-journal panel, laid out side by side or stacked depending on terminal size.
- [ ] 70. A thin state/action layer between the dashboard and `curses` itself (what's focused, what a keypress does to the underlying stores) kept separate from the actual screen-drawing code, so that layer can be unit-tested without a real terminal -- `curses` itself can't run under `pytest` without one.
- [ ] 71. Task panel becomes interactive: arrow keys/`j`/`k` to move the selection, `space`/`enter` to toggle a task done, writing through to the real `TaskStore`/`SqliteTaskStore` (whichever backend is active) rather than a separate copy of the data.
- [ ] 72. Habit panel becomes interactive: a keypress checks in the selected habit, reusing `cmd_habit_check`'s existing streak logic rather than duplicating it.
- [ ] 73. `Tab`/`shift+Tab` to switch which panel has focus, `q` to quit, and the existing `color.py` palette reused for priorities/overdue/streaks so the dashboard looks consistent with the plain-CLI output instead of introducing its own color scheme.
- [ ] 74. Graceful fallback: `onepact ui` on a terminal too small for the layout, or on a platform/environment where `curses` can't initialize (e.g. output piped to a file), prints a clear error instead of crashing.
- [ ] 75. README section documenting `onepact ui`: what it shows, its keybindings, and that it's optional -- every existing command is unaffected.

---

When you reach the end of this list, don't leave it empty: propose the next
phase yourself, in this same format, based on what would make the tool
genuinely more useful — not filler.
