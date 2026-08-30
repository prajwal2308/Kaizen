# kaizen

A local-first CLI for tasks, journaling, and daily review — built one small,
real increment at a time. See [ROADMAP.md](ROADMAP.md) for the running build
log and what's next, and [CHANGELOG.md](CHANGELOG.md) for what shipped when.

## Also in this repo

[`reelnotes/`](reelnotes/README.md) is a separate side project that shares the
repo but not the codebase: send an Instagram reel to it as a DM — the same
gesture as sending it to a friend — and it transcribes the video, extracts a
structured note, and replies in the thread with the takeaway. An iOS Shortcut
covers links shared from outside Instagram. It has its own dependencies, tests,
and CI job.

## Why

Kaizen (改善) means "continuous improvement." This project is exactly that:
no big-bang rewrite, no scope creep — just a working tool that gets a little
better every day.

## Install (development)

```bash
git clone https://github.com/prajwal2308/kaizen.git
cd kaizen
pip install -e .
```

## Usage

```bash
kaizen add "write the weekly review"
kaizen add "renew passport" --priority high
kaizen add "pay rent" --due 2026-09-01
kaizen add "mow the lawn" --tag home --tag chores
kaizen list
kaizen list --tag home
kaizen show 1
kaizen edit 1 "write and send the weekly review"
kaizen done 1
kaizen list --all
kaizen rm 1
```

Tasks are stored as JSON in `~/.kaizen/tasks.json`.

## Development

```bash
pip install -e . pytest ruff
pytest -q
ruff check src tests
```

## Status

Early days — see [ROADMAP.md](ROADMAP.md) for the current phase and what's
planned next.
