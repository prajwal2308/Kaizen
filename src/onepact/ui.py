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
from dataclasses import dataclass

from onepact.storage import Entry, Habit, Task, is_overdue, priority_rank

_JOURNAL_PANEL_LIMIT = 5
PANELS = ("tasks", "habits", "journal")


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


@dataclass(frozen=True)
class DashboardState:
    """Which panel has focus, and which line is selected within each
    panel. Deliberately knows nothing about tasks/habits/journal entries
    as data -- just indices -- so it (and `handle_key` below) can be
    unit-tested without loading any store or touching `curses` beyond
    the key-code constants, which don't need a real terminal either.
    """

    focus: int = 0
    selected: tuple[int, int, int] = (0, 0, 0)

    @property
    def focused_panel(self) -> str:
        return PANELS[self.focus]


_QUIT_KEYS = {ord("q"), ord("Q")}
_FOCUS_NEXT_KEYS = {ord("\t")}
_FOCUS_PREV_KEYS = {curses.KEY_BTAB}
_SELECT_DOWN_KEYS = {curses.KEY_DOWN, ord("j")}
_SELECT_UP_KEYS = {curses.KEY_UP, ord("k")}
_ACTIVATE_KEYS = {ord(" "), ord("\n"), curses.KEY_ENTER}


def handle_key(
    state: DashboardState, key: int, panel_lengths: tuple[int, int, int]
) -> tuple[DashboardState, str | None]:
    """Given the dashboard's current state, a curses keycode, and how
    many selectable items each panel currently has (tasks, habits,
    journal, in that order -- matching `PANELS`), returns the new state
    and an action: `"quit"`, `"activate"` (something should happen to
    whichever item is selected in the focused panel -- deciding what
    is items 71/72's job, not this function's, since no store is
    touched here), or `None` for a key that was fully handled by just
    updating navigation state, or that wasn't recognized at all (in
    which case `state` comes back unchanged).
    """
    if key in _QUIT_KEYS:
        return state, "quit"
    if key in _FOCUS_NEXT_KEYS:
        return DashboardState(focus=(state.focus + 1) % len(PANELS), selected=state.selected), None
    if key in _FOCUS_PREV_KEYS:
        return DashboardState(focus=(state.focus - 1) % len(PANELS), selected=state.selected), None
    if key in _SELECT_DOWN_KEYS or key in _SELECT_UP_KEYS:
        length = panel_lengths[state.focus]
        if length == 0:
            return state, None
        delta = 1 if key in _SELECT_DOWN_KEYS else -1
        new_index = (state.selected[state.focus] + delta) % length
        a, b, c = state.selected
        indices = [a, b, c]
        indices[state.focus] = new_index
        new_selected = (indices[0], indices[1], indices[2])
        return DashboardState(focus=state.focus, selected=new_selected), None
    if key in _ACTIVATE_KEYS:
        return state, "activate"
    return state, None


_SIDE_BY_SIDE_MIN_WIDTH = 100


def _draw_panel(
    win: curses.window,
    title: str,
    lines: list[str],
    focused: bool,
    selected_index: int | None,
) -> None:
    win.erase()
    win.border()
    height, width = win.getmaxyx()
    title_attr = curses.A_BOLD | curses.A_REVERSE if focused else curses.A_NORMAL
    win.addnstr(0, 2, f" {title} ", max(width - 4, 0), title_attr)
    for i, line in enumerate(lines[: max(height - 2, 0)]):
        line_attr = curses.A_REVERSE if i == selected_index else curses.A_NORMAL
        win.addnstr(i + 1, 1, line, max(width - 2, 0), line_attr)
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


_PANEL_TITLES = ("Tasks", "Habits", "Journal")


def _render(
    stdscr: curses.window,
    tasks: list[Task],
    habits: list[Habit],
    entries: list[Entry],
    today: str,
) -> None:
    curses.curs_set(0)
    state = DashboardState()
    while True:
        stdscr.erase()
        stdscr.noutrefresh()
        height, width = stdscr.getmaxyx()
        layout = _layout(height, width)

        panel_lines = (
            task_lines(tasks, today),
            habit_lines(habits, today),
            journal_lines(entries),
        )
        panel_lengths = (
            sum(1 for t in tasks if not t.done),
            len(habits),
            min(len(entries), _JOURNAL_PANEL_LIMIT),
        )

        for i, ((win_height, win_width, y, x), title, lines) in enumerate(
            zip(layout, _PANEL_TITLES, panel_lines)
        ):
            win = curses.newwin(win_height, win_width, y, x)
            focused = i == state.focus
            selected_index = state.selected[i] if focused else None
            _draw_panel(win, title, lines, focused, selected_index)

        curses.doupdate()
        key = stdscr.getch()
        state, action = handle_key(state, key, panel_lengths)
        if action == "quit":
            return


def run(tasks: list[Task], habits: list[Habit], entries: list[Entry], today: str) -> int:
    try:
        curses.wrapper(_render, tasks, habits, entries, today)
    except curses.error as exc:
        print(f"Could not start the terminal UI: {exc}", file=sys.stderr)
        return 1
    return 0
