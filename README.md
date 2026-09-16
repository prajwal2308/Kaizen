# onepact

A local-first CLI for tasks, journaling, and daily review — built one small,
real increment at a time. See [ROADMAP.md](ROADMAP.md) for the running build
log and what's next, and [CHANGELOG.md](CHANGELOG.md) for what shipped when.

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

Tasks are stored as JSON in `~/.onepact/tasks.json`.

## Configuration

Create `~/.onepact/config.toml` to change defaults:

```toml
# ~/.onepact/config.toml
priority = "high"
```

Right now the only supported key is `priority` — the default `add` uses
when `--priority` is omitted (an explicit `--priority` still wins). An
invalid value falls back to `med` rather than erroring. There's no
`config` command yet to view or edit this from the CLI; edit the file
directly for now.

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

## Development

```bash
pip install -e . pytest ruff
pytest -q
ruff check src tests
```

## Status

Early days — see [ROADMAP.md](ROADMAP.md) for the current phase and what's
planned next.
