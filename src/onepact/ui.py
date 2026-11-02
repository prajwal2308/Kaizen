"""Full-screen `curses` dashboard (`onepact ui`), additive on top of the
regular one-shot commands -- every `onepact <command>` keeps working
exactly as before. This module intentionally knows nothing about which
backend is active or how to load one; `cli.cmd_ui` loads the real stores
and hands this module plain lists of `Task`/`Habit`/`Entry`, so the
panel-building functions below can be unit-tested without a terminal.
Only `run()` and below touch `curses` itself.
"""

from __future__ import annotations

import curses
import sys

from onepact.storage import Entry, Habit, Task, is_overdue, priority_rank

_JOURNAL_PANEL_LIMIT = 5


def task_lines(tasks: list[Task], today: str) -> list[str]:
    pending = sorted(
        (t for t in tasks if not t.done),
        key=lambda t: (priority_rank(t.priority), t.id),
    )
    if not pending:
        return ["No tasks."]
    lines = []
    for t in pending:
        line = f"#{t.id} ({t.priority}) {t.title}"
        if t.due:
            line += f" [due {t.due}]"
            if is_overdue(t, today):
                line += " OVERDUE"
        lines.append(line)
    return lines


def habit_lines(habits: list[Habit], today: str) -> list[str]:
    if not habits:
        return ["No habits."]
    lines = []
    for h in habits:
        line = f"{h.name} [{h.frequency}] streak:{h.streak}"
        if h.last_checked == today:
            line += " (checked in today)"
        lines.append(line)
    return lines


def journal_lines(entries: list[Entry]) -> list[str]:
    if not entries:
        return ["No journal entries."]
    recent = list(reversed(entries))[:_JOURNAL_PANEL_LIMIT]
    lines = []
    for e in recent:
        first_line = e.body.splitlines()[0] if e.body else ""
        lines.append(f"#{e.id} [{e.created_at[:10]}] {first_line}")
    return lines


_SIDE_BY_SIDE_MIN_WIDTH = 100


def _draw_panel(win: curses.window, title: str, lines: list[str]) -> None:
    win.erase()
    win.border()
    height, width = win.getmaxyx()
    win.addnstr(0, 2, f" {title} ", max(width - 4, 0))
    for i, line in enumerate(lines[: max(height - 2, 0)]):
        win.addnstr(i + 1, 1, line, max(width - 2, 0))
    win.noutrefresh()


def _layout(height: int, width: int) -> tuple[tuple[int, int, int, int], ...]:
    """Returns (height, width, y, x) for the task/habit/journal windows,
    in that order -- three columns side by side on a wide terminal,
    stacked rows otherwise.
    """
    if width >= _SIDE_BY_SIDE_MIN_WIDTH:
        col = width // 3
        last_col = width - 2 * col
        return ((height, col, 0, 0), (height, col, 0, col), (height, last_col, 0, 2 * col))
    row = height // 3
    last_row = height - 2 * row
    return ((row, width, 0, 0), (row, width, row, 0), (last_row, width, 2 * row, 0))


def _render(
    stdscr: curses.window,
    tasks: list[Task],
    habits: list[Habit],
    entries: list[Entry],
    today: str,
) -> None:
    curses.curs_set(0)
    stdscr.erase()
    stdscr.noutrefresh()
    height, width = stdscr.getmaxyx()
    layout = _layout(height, width)

    panels = (
        ("Tasks", task_lines(tasks, today)),
        ("Habits", habit_lines(habits, today)),
        ("Journal", journal_lines(entries)),
    )
    for (win_height, win_width, y, x), (title, lines) in zip(layout, panels):
        win = curses.newwin(win_height, win_width, y, x)
        _draw_panel(win, title, lines)

    curses.doupdate()
    stdscr.getch()


def run(tasks: list[Task], habits: list[Habit], entries: list[Entry], today: str) -> int:
    try:
        curses.wrapper(_render, tasks, habits, entries, today)
    except curses.error as exc:
        print(f"Could not start the terminal UI: {exc}", file=sys.stderr)
        return 1
    return 0
