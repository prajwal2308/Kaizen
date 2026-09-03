from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

from onepact.storage import (
    PRIORITIES,
    Entry,
    JournalStore,
    Task,
    TaskStore,
    is_overdue,
    priority_rank,
)


def _parse_due(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"invalid due date {value!r}, expected YYYY-MM-DD"
        ) from None
    return value


def _positive_int(value: str) -> int:
    try:
        n = int(value)
    except ValueError:
        n = None
    if n is None or n < 1:
        raise argparse.ArgumentTypeError(
            f"invalid limit {value!r}, expected a positive integer"
        )
    return n


def cmd_add(store: TaskStore, args: argparse.Namespace) -> int:
    tasks = store.load()
    tags = list(dict.fromkeys(args.tags or []))
    task = Task(
        id=store.next_id(tasks),
        title=args.title,
        priority=args.priority,
        due=args.due,
        tags=tags,
    )
    tasks.append(task)
    store.save(tasks)
    print(f"Added #{task.id}: {task.title}")
    return 0


def cmd_list(store: TaskStore, args: argparse.Namespace) -> int:
    tasks = store.load()
    if not args.all:
        tasks = [t for t in tasks if not t.done]
    if args.tag:
        tasks = [t for t in tasks if args.tag in t.tags]
    if not tasks:
        print("No tasks.")
        return 0
    tasks.sort(key=lambda t: (priority_rank(t.priority), t.id))
    today = datetime.now(timezone.utc).date().isoformat()
    for t in tasks:
        mark = "x" if t.done else " "
        line = f"[{mark}] #{t.id} ({t.priority}) {t.title}"
        if t.due:
            line += f" [due {t.due}]"
            if is_overdue(t, today):
                line += " OVERDUE"
        if t.tags:
            line += f" [tags: {', '.join(t.tags)}]"
        print(line)
    return 0


def cmd_show(store: TaskStore, args: argparse.Namespace) -> int:
    tasks = store.load()
    for t in tasks:
        if t.id == args.id:
            today = datetime.now(timezone.utc).date().isoformat()
            print(f"#{t.id} {t.title}")
            print(f"Status: {'done' if t.done else 'pending'}")
            print(f"Priority: {t.priority}")
            due_line = f"Due: {t.due}" if t.due else "Due: (none)"
            if t.due and is_overdue(t, today):
                due_line += " (OVERDUE)"
            print(due_line)
            print(f"Tags: {', '.join(t.tags) if t.tags else '(none)'}")
            print(f"Created: {t.created_at}")
            if t.done_at:
                print(f"Completed: {t.done_at}")
            return 0
    print(f"No task with id {args.id}", file=sys.stderr)
    return 1


def cmd_done(store: TaskStore, args: argparse.Namespace) -> int:
    tasks = store.load()
    for t in tasks:
        if t.id == args.id:
            t.done = True
            t.done_at = datetime.now(timezone.utc).isoformat()
            store.save(tasks)
            print(f"Marked #{t.id} done.")
            return 0
    print(f"No task with id {args.id}", file=sys.stderr)
    return 1


def cmd_edit(store: TaskStore, args: argparse.Namespace) -> int:
    tasks = store.load()
    for t in tasks:
        if t.id == args.id:
            t.title = args.title
            store.save(tasks)
            print(f"Edited #{t.id}: {t.title}")
            return 0
    print(f"No task with id {args.id}", file=sys.stderr)
    return 1


def _read_entry_from_editor() -> str:
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vi"
    fd, tmp_path = tempfile.mkstemp(suffix=".md", prefix="onepact-journal-")
    os.close(fd)
    try:
        subprocess.run([editor, tmp_path], check=True)
        with open(tmp_path, encoding="utf-8") as f:
            return f.read()
    finally:
        os.remove(tmp_path)


def cmd_journal(store: JournalStore, args: argparse.Namespace) -> int:
    if args.text is not None:
        body = args.text
    else:
        try:
            body = _read_entry_from_editor()
        except (OSError, subprocess.CalledProcessError) as exc:
            print(f"Could not open editor: {exc}", file=sys.stderr)
            return 1
    body = body.strip()
    if not body:
        print("Empty entry, nothing journaled.", file=sys.stderr)
        return 1
    entries = store.load()
    entry = Entry(id=store.next_id(entries), body=body)
    entries.append(entry)
    store.save(entries)
    print(f"Journaled #{entry.id}")
    return 0


def cmd_journal_list(store: JournalStore, args: argparse.Namespace) -> int:
    entries = list(reversed(store.load()))
    if args.limit is not None:
        entries = entries[: args.limit]
    if not entries:
        print("No journal entries.")
        return 0
    for e in entries:
        first_line = e.body.splitlines()[0] if e.body else ""
        print(f"#{e.id} [{e.created_at}] {first_line}")
    return 0


def cmd_rm(store: TaskStore, args: argparse.Namespace) -> int:
    tasks = store.load()
    remaining = [t for t in tasks if t.id != args.id]
    if len(remaining) == len(tasks):
        print(f"No task with id {args.id}", file=sys.stderr)
        return 1
    store.save(remaining)
    print(f"Removed #{args.id}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="onepact", description="A local-first task and journal CLI."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Add a new task")
    p_add.add_argument("title", help="Task title")
    p_add.add_argument(
        "--priority",
        choices=PRIORITIES,
        default="med",
        help="Task priority (default: med)",
    )
    p_add.add_argument(
        "--due",
        type=_parse_due,
        default=None,
        help="Due date as YYYY-MM-DD",
    )
    p_add.add_argument(
        "--tag",
        dest="tags",
        action="append",
        default=None,
        help="Tag the task (repeatable)",
    )
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="List tasks")
    p_list.add_argument("--all", action="store_true", help="Include completed tasks")
    p_list.add_argument("--tag", default=None, help="Filter to tasks with this tag")
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="Show full details for a task")
    p_show.add_argument("id", type=int, help="Task id")
    p_show.set_defaults(func=cmd_show)

    p_done = sub.add_parser("done", help="Mark a task done")
    p_done.add_argument("id", type=int, help="Task id")
    p_done.set_defaults(func=cmd_done)

    p_edit = sub.add_parser("edit", help="Edit a task's title")
    p_edit.add_argument("id", type=int, help="Task id")
    p_edit.add_argument("title", help="New task title")
    p_edit.set_defaults(func=cmd_edit)

    p_rm = sub.add_parser("rm", help="Remove a task")
    p_rm.add_argument("id", type=int, help="Task id")
    p_rm.set_defaults(func=cmd_rm)

    p_journal = sub.add_parser("journal", help="Manage journal entries")
    journal_sub = p_journal.add_subparsers(dest="journal_command", required=True)

    p_journal_add = journal_sub.add_parser("add", help="Append a journal entry")
    p_journal_add.add_argument(
        "text",
        nargs="?",
        default=None,
        help="Journal entry text (omit to write a longer entry in $EDITOR)",
    )
    p_journal_add.set_defaults(func=cmd_journal, store_type="journal")

    p_journal_list = journal_sub.add_parser(
        "list", help="List journal entries, most recent first"
    )
    p_journal_list.add_argument(
        "--limit",
        type=_positive_int,
        default=None,
        help="Show at most this many entries",
    )
    p_journal_list.set_defaults(func=cmd_journal_list, store_type="journal")

    return parser


_JOURNAL_SUBCOMMANDS = {"add", "list"}


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    argv = list(argv)
    if argv and argv[0] == "journal":
        rest = argv[1:]
        if not rest or rest[0] not in _JOURNAL_SUBCOMMANDS:
            argv = ["journal", "add", *rest]

    parser = build_parser()
    args = parser.parse_args(argv)
    store = JournalStore() if getattr(args, "store_type", "task") == "journal" else TaskStore()
    return args.func(store, args)


if __name__ == "__main__":
    raise SystemExit(main())
