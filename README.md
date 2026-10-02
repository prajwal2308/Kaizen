# onepact

A local-first CLI for tasks, journaling, and daily review — built one small,
real increment at a time. See [ROADMAP.md](ROADMAP.md) for the running build
log and what's next, and [CHANGELOG.md](CHANGELOG.md) for what shipped when.
[SCHEMA.md](SCHEMA.md) designs the SQLite schema implemented by
`SqliteTaskStore` (`src/onepact/sqlite_storage.py`), which is the default
task storage backend as of this release; see
[Storage backend](#storage-backend) below.

## Why

One pact with yourself, kept one day at a time: no big-bang rewrite, no
scope creep — just a working tool that gets a little better every day.

## Install (development)

```bash
git clone https://github.com/prajwal2308/onepact.git
cd onepact
pip install -e .
```

## Usage

```bash
onepact add "write the weekly review"
onepact add "renew passport" --priority high
onepact add "pay rent" --due 2026-09-01
onepact add "mow the lawn" --tag home --tag chores --priority high
onepact add "take out the trash" --repeat weekly
onepact list
onepact list --tag home
onepact list --priority high
onepact list --tag home --priority high
onepact list --sort due
onepact list --overdue
onepact find passport
onepact show 1
onepact edit 1 "write and send the weekly review"
onepact done 1
onepact done 5
onepact list --all
onepact rm 1
```

`find` searches task titles with a case-insensitive substring match; like
`list`, it hides completed tasks unless you pass `--all`.

`list --tag <t>`, `--priority <p>`, and `--overdue` all combine — pass
several to narrow down further, e.g. `list --tag home --priority high`
shows only high-priority tasks tagged `home`.

`list --sort {priority,due,created}` controls ordering: `priority` (the
default) shows high-priority tasks first, `due` shows the soonest due
date first with undated tasks last, and `created` shows the oldest task
first.

`list --overdue` is shorthand for showing only past-due, unfinished
tasks — the same ones flagged `OVERDUE` in a regular `list`.

`--repeat {daily,weekly}` on `add` marks a task as recurring, shown as
`[repeat: daily]`/`[repeat: weekly]` in `list` and `find`, and as a
`Repeat:` line in `show`. Running `done` on a recurring task marks it
done as usual and creates the next occurrence — same title, priority,
tags, and repeat setting — due one day (`daily`) or one week (`weekly`)
from today.

Tasks are stored in `~/.onepact/onepact.db` (SQLite) by default; see
[Storage backend](#storage-backend) for how to use JSON instead.

## Storage backend

```bash
onepact config set backend sqlite   # default
onepact config set backend json
onepact migrate json-to-sqlite
```

Tasks are stored either as a SQLite database (`~/.onepact/onepact.db`,
schema: [SCHEMA.md](SCHEMA.md)) or as JSON (`~/.onepact/tasks.json`),
controlled by the `backend` config key — `sqlite` is the default, `json`
is kept for compatibility with earlier releases. The first time the
sqlite backend is used and `onepact.db` doesn't exist yet, any tasks
already in `tasks.json` are copied over automatically, so upgrading
doesn't strand existing data behind a manual step. After that first copy
the two stores are independent — further changes to one aren't reflected
in the other, so switching `backend` back and forth won't merge them.

`onepact migrate json-to-sqlite` does the same copy explicitly and on
demand: it's a copy, not a move (`tasks.json` is untouched either way),
and it refuses to run again once `onepact.db` already has tasks in it, so
it can't accidentally double up or overwrite data. It always reads from
the JSON store and writes to the SQLite store by name, regardless of
which backend is currently active.

## Export & import

```bash
onepact export --format json
onepact export --format csv
onepact export --format json --output backup.json
onepact export --format csv -o tasks.csv
onepact import backup.json
onepact import tasks.csv
onepact import some-file --format json
```

`export` prints every task from whichever backend is currently active as
JSON or CSV; add `--output`/`-o <file>` to write to a file instead of
stdout. The `json` format is the same array-of-objects shape as
`tasks.json`, so it's a full-fidelity dump of every field. The `csv`
format has one row per task with a header
(`id,title,priority,due,done,done_at,created_at,tags,repeat`); `tags` are
joined with `;` since a task can have several and CSV already uses `,`
as its own delimiter.

`import <file>` reads tasks back from a file `export` produced (or any
file in the same shape) and adds them to whichever backend is currently
active, so `export` and `import` round-trip a task list. The format is
inferred from the file's `.json`/`.csv` extension, or set explicitly with
`--format`. Every field carries over except `id` — each imported task
gets a fresh one from the active store, so importing never overwrites or
collides with tasks you already have; run it against an empty store (or
a fresh backend) if you want an exact restore, including ids.

## Data & backups

Everything onepact stores lives under `~/.onepact/`:

| Path                    | What it is                                              |
| ------------------------ | -------------------------------------------------------- |
| `onepact.db`             | Tasks, if `backend` is `sqlite` (the default)             |
| `tasks.json`              | Tasks, if `backend` is `json`                             |
| `journal.json`            | Journal entries — always JSON, regardless of `backend`    |
| `habits.json`              | Habits — always JSON, regardless of `backend`            |
| `config.toml`              | Settings written by `config set` (or edited by hand)     |
| `backups/`                 | Timestamped snapshots made before `rm`/`migrate` write    |
| `.undo.json`                | Pointer used by `undo`; managed automatically             |

```bash
onepact undo
```

`rm` and `migrate json-to-sqlite` copy the file they're about to
overwrite into `~/.onepact/backups/` (timestamped) before writing, so a
mistaken removal or migration always has a copy to recover from. Nothing
is backed up the first time either command runs against a fresh data
directory — there's nothing there yet to protect.

`onepact undo` reverts the most recent `rm` or `migrate`, restoring
whatever it backed up. It's a single-level undo: only the very last
reversible action can be undone, so running `undo` twice in a row (with
nothing destructive in between) reports "Nothing to undo" the second
time rather than reaching further back — even if older backups are
still sitting in `backups/` from earlier in the day.

These automatic backups protect against a bad `rm` or `migrate`, but
they live inside `~/.onepact/` itself, so they're no help if that whole
directory is lost, moved, or corrupted. For real disaster recovery, use
[`export`](#export--import) to write a copy of your tasks somewhere
else entirely — a synced folder, another drive, version control — on
whatever cadence matters to you; `import` brings it back on a fresh
install or after a real loss, not just a single bad command.

## Configuration

```bash
onepact config show
onepact config set priority high
```

`config show` prints the current configuration; `config set <key> <value>`
writes a value to `~/.onepact/config.toml` (creating it if needed) and
rejects unknown keys, or invalid values for a known key (`priority` must
be `low`/`med`/`high`, `backend` must be `sqlite`/`json`) — nothing is
written on an invalid `set`. Supported keys: `priority` — the default
`add` uses when `--priority` is omitted (an explicit `--priority` still
wins) — and `backend` — which task store `onepact` uses, see
[Storage backend](#storage-backend). You can also edit the file directly:

```toml
# ~/.onepact/config.toml
priority = "high"
backend = "json"
```

## Color

`list`, `find`, `show`, `journal list`, and `journal search` colorize
priorities, `OVERDUE`, tags, `repeat`, and linked-task markers when
standard output is a real terminal. Color is off automatically when
output is piped or redirected, and can be turned off on a terminal too
by setting the `NO_COLOR` environment variable (to any value, including
empty — see [no-color.org](https://no-color.org)). There's no separate
`--color`/`--no-color` flag; it's autodetected.

## Journaling

```bash
onepact journal "wrote the weekly review"
onepact journal "drafted the proposal" --task 1
onepact journal
onepact journal list
onepact journal list --limit 5
onepact journal show 1
onepact journal search proposal
onepact journal rm 1
onepact journal rm 1 --yes
```

Journal entries are free-form, timestamped notes, separate from tasks.
Run `onepact journal "text"` to append one directly, or `onepact journal`
with no text to open `$EDITOR` (falling back to `$VISUAL`, then `vi`) for
something longer — an empty entry, whether from a closed editor or from
`journal "   "`, is discarded rather than saved.

Add `--task <id>` to link an entry to an existing task (rejected if the
task doesn't exist); `journal list` and `journal show` display the link
when present. `journal list` shows entries most recent first, one line
each, optionally capped with `--limit N`. `journal show <id>` prints an
entry's full body. `journal search <text>` does a case-insensitive
substring search across entry bodies, most recent match first.
`journal rm <id>` asks for confirmation before deleting; pass `--yes`
(or `-y`) to skip the prompt.

Entries are stored as JSON in `~/.onepact/journal.json`, separate from
`tasks.json`.

## Habits

```bash
onepact habit add "exercise" --daily
onepact habit add "review inbox" --weekly
```

`habit add <name>` creates a new habit to track, with exactly one of
`--daily`/`--weekly` saying how often you intend to check in on it — more
habit commands (checking one off, listing current streaks) are coming in
later releases. A name can only be added once; adding it again errors
out rather than creating a second habit with the same name, since name
is how every habit command refers to one.

Habits are stored as JSON in `~/.onepact/habits.json`, separate from
tasks and journal entries.

## Development

```bash
pip install -e . pytest ruff
pytest -q
ruff check src tests
```

## Status

Early days — see [ROADMAP.md](ROADMAP.md) for the current phase and what's
planned next.
