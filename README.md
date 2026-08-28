# kaizen

A local-first CLI for tasks, journaling, and daily review — built one small,
real increment at a time. See [ROADMAP.md](ROADMAP.md) for the running build
log and what's next, and [CHANGELOG.md](CHANGELOG.md) for what shipped when.

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
kaizen list
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
