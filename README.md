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
onepact add "mow the lawn" --tag home --tag chores
onepact list
onepact list --tag home
onepact show 1
onepact edit 1 "write and send the weekly review"
onepact done 1
onepact list --all
onepact rm 1
```

Tasks are stored as JSON in `~/.onepact/tasks.json`.

## Journaling

```bash
onepact journal "wrote the weekly review"
onepact journal "drafted the proposal" --task 1
onepact journal
onepact journal list
onepact journal list --limit 5
onepact journal show 1
onepact journal search proposal
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
