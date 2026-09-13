from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

from onepact.storage import (
    PRIORITIES,
    REPEATS,
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
        repeat=args.repeat,
    )
    tasks.append(task)
    store.save(tasks)
    print(f"Added #{task.id}: {task.title}")
    return 0


def _format_task_line(t: Task, today: str) -> str:
    mark = "x" if t.done else " "
    line = f"[{mark}] #{t.id} ({t.priority}) {t.title}"
    if t.due:
        line += f" [due {t.due}]"
        if is_overdue(t, today):
            line += " OVERDUE"
    if t.tags:
        line += f" [tags: {', '.join(t.tags)}]"
    if t.repeat:
        line += f" [repeat: {t.repeat}]"
    return line


def cmd_list(store: TaskStore, args: argparse.Namespace) -> int:
    tasks = store.load()
    if not args.all:
        tasks = [t for t in tasks if not t.done]
    if args.tag:
        tasks = [t for t in tasks if args.tag in t.tags]
    today = datetime.now(timezone.utc).date().isoformat()
    if args.overdue:
        tasks = [t for t in tasks if is_overdue(t, today)]
    if not tasks:
        print("No tasks.")
        return 0
    if args.sort == "due":
        tasks.sort(key=lambda t: (t.due is None, t.due or "", t.id))
    elif args.sort == "created":
        tasks.sort(key=lambda t: (t.created_at, t.id))
    else:
        tasks.sort(key=lambda t: (priority_rank(t.priority), t.id))
    for t in tasks:
        print(_format_task_line(t, today))
    return 0


def cmd_find(store: TaskStore, args: argparse.Namespace) -> int:
    tasks = store.load()
    if not args.all:
        tasks = [t for t in tasks if not t.done]
    query = args.text.lower()
    matches = [t for t in tasks if query in t.title.lower()]
    if not matches:
        print("No matching tasks.")
        return 0
    matches.sort(key=lambda t: (priority_rank(t.priority), t.id))
    today = datetime.now(timezone.utc).date().isoformat()
    for t in matches:
        print(_format_task_line(t, today))
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
            print(f"Repeat: {t.repeat}" if t.repeat else "Repeat: (none)")
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
    task_id = args.task
    if task_id is not None and not any(t.id == task_id for t in TaskStore().load()):
        print(f"No task with id {task_id}", file=sys.stderr)
        return 1
    entries = store.load()
    entry = Entry(id=store.next_id(entries), body=body, task_id=task_id)
    entries.append(entry)
    store.save(entries)
    suffix = f" (linked to task #{task_id})" if task_id is not None else ""
    print(f"Journaled #{entry.id}{suffix}")
    return 0


def _format_entry_line(e: Entry) -> str:
    first_line = e.body.splitlines()[0] if e.body else ""
    line = f"#{e.id} [{e.created_at}] {first_line}"
    if e.task_id is not None:
        line += f" [task #{e.task_id}]"
    return line


def cmd_journal_list(store: JournalStore, args: argparse.Namespace) -> int:
    entries = list(reversed(store.load()))
    if args.limit is not None:
        entries = entries[: args.limit]
    if not entries:
        print("No journal entries.")
        return 0
    for e in entries:
        print(_format_entry_line(e))
    return 0


def cmd_journal_search(store: JournalStore, args: argparse.Namespace) -> int:
    entries = list(reversed(store.load()))
    query = args.text.lower()
    matches = [e for e in entries if query in e.body.lower()]
    if not matches:
        print("No matching journal entries.")
        return 0
    for e in matches:
        print(_format_entry_line(e))
    return 0


def cmd_journal_show(store: JournalStore, args: argparse.Namespace) -> int:
    entries = store.load()
    for e in entries:
        if e.id == args.id:
            print(f"#{e.id} [{e.created_at}]")
            print(f"Task: #{e.task_id}" if e.task_id is not None else "Task: (none)")
            print(e.body)
            return 0
    print(f"No journal entry with id {args.id}", file=sys.stderr)
    return 1


def _confirm(prompt: str) -> bool:
    try:
        answer = input(f"{prompt} [y/N] ")
    except EOFError:
        return False
    return answer.strip().lower() in ("y", "yes")


def cmd_journal_rm(store: JournalStore, args: argparse.Namespace) -> int:
    entries = store.load()
    entry = next((e for e in entries if e.id == args.id), None)
    if entry is None:
        print(f"No journal entry with id {args.id}", file=sys.stderr)
        return 1
    if not args.yes:
        preview = entry.body.splitlines()[0] if entry.body else ""
        if not _confirm(f"Remove journal entry #{entry.id} ({preview!r})?"):
            print("Aborted.")
            return 1
    remaining = [e for e in entries if e.id != args.id]
    store.save(remaining)
    print(f"Removed #{args.id}")
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
    p_add.add_argument(
        "--repeat",
        choices=REPEATS,
        default=None,
        help="Make this task recur daily or weekly",
    )
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="List tasks")
    p_list.add_argument("--all", action="store_true", help="Include completed tasks")
    p_list.add_argument("--tag", default=None, help="Filter to tasks with this tag")
    p_list.add_argument(
        "--overdue", action="store_true", help="Show only overdue tasks"
    )
    p_list.add_argument(
        "--sort",
        choices=("priority", "due", "created"),
        default="priority",
        help="Sort order (default: priority)",
    )
    p_list.set_defaults(func=cmd_list)

    p_find = sub.add_parser("find", help="Search task titles by substring")
    p_find.add_argument("text", help="Substring to search for (case-insensitive)")
    p_find.add_argument("--all", action="store_true", help="Include completed tasks")
    p_find.set_defaults(func=cmd_find)

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
    p_journal_add.add_argument(
        "--task",
        type=int,
        default=None,
        help="Link this entry to task <id>",
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

    p_journal_show = journal_sub.add_parser("show", help="Show a single journal entry")
    p_journal_show.add_argument("id", type=int, help="Entry id")
    p_journal_show.set_defaults(func=cmd_journal_show, store_type="journal")

    p_journal_search = journal_sub.add_parser(
        "search", help="Search journal entries by substring"
    )
    p_journal_search.add_argument("text", help="Substring to search for (case-insensitive)")
    p_journal_search.set_defaults(func=cmd_journal_search, store_type="journal")

    p_journal_rm = journal_sub.add_parser("rm", help="Remove a journal entry")
    p_journal_rm.add_argument("id", type=int, help="Entry id")
    p_journal_rm.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip the confirmation prompt",
    )
    p_journal_rm.set_defaults(func=cmd_journal_rm, store_type="journal")

    return parser


_JOURNAL_SUBCOMMANDS = {"add", "list", "show", "search", "rm"}


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
