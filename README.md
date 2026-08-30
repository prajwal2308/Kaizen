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

## Development

```bash
pip install -e . pytest ruff
pytest -q
ruff check src tests
```

## Status

Early days — see [ROADMAP.md](ROADMAP.md) for the current phase and what's
planned next.
