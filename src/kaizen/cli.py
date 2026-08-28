from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from kaizen.storage import PRIORITIES, Task, TaskStore, is_overdue, priority_rank


def _parse_due(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"invalid due date {value!r}, expected YYYY-MM-DD"
        ) from None
    return value


def cmd_add(store: TaskStore, args: argparse.Namespace) -> int:
    tasks = store.load()
    task = Task(id=store.next_id(tasks), title=args.title, priority=args.priority, due=args.due)
    tasks.append(task)
    store.save(tasks)
    print(f"Added #{task.id}: {task.title}")
    return 0


def cmd_list(store: TaskStore, args: argparse.Namespace) -> int:
    tasks = store.load()
    if not args.all:
        tasks = [t for t in tasks if not t.done]
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
        print(line)
    return 0


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
        prog="kaizen", description="A local-first task and journal CLI."
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
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="List tasks")
    p_list.add_argument("--all", action="store_true", help="Include completed tasks")
    p_list.set_defaults(func=cmd_list)

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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    store = TaskStore()
    return args.func(store, args)


if __name__ == "__main__":
    raise SystemExit(main())
