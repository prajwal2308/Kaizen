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
import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from onepact.editor import read_entry_from_editor
from onepact.storage import (
    Entry,
    Habit,
    Task,
    check_in_habit,
    complete_task,
    is_due_today,
    is_overdue,
    priority_rank,
)

# Mirrors cli.py's own _PRIORITY_COLOR -- kept as a separate small, static
# copy rather than importing it, since cli.py already imports this module
# (importing the other way back would be circular) and this mapping is
# tiny and effectively never changes, unlike the recurring-task/streak
# logic shared via storage.complete_task()/check_in_habit().
_PRIORITY_COLOR = {"high": "red", "med": "yellow", "low": "blue"}


def task_line_color(t: Task, today: str) -> str:
    """The same palette `cli.py`'s plain-text output uses for a task
    line: red for an overdue task (overriding its priority color, since
    overdue is the more urgent signal), cyan for one due today (still
    more urgent than priority, but a task is never both), otherwise its
    priority's color.
    """
    if is_overdue(t, today):
        return "red"
    if is_due_today(t, today):
        return "cyan"
    return _PRIORITY_COLOR[t.priority]


def habit_line_color(h: Habit, today: str) -> str:
    """Green if checked in today (the more relevant signal when
    present), otherwise magenta -- the same color `cli.py` uses for a
    habit's streak number.
    """
    return "green" if h.last_checked == today else "magenta"

_JOURNAL_PANEL_LIMIT = 5
PANELS = ("tasks", "habits", "journal")


def _pending_tasks(tasks: list[Task]) -> list[Task]:
    return sorted(
        (t for t in tasks if not t.done),
        key=lambda t: (priority_rank(t.priority), t.id),
    )


def task_lines(tasks: list[Task], today: str) -> list[str]:
    pending = _pending_tasks(tasks)
    if not pending:
        return ["No tasks."]
    lines = []
    for t in pending:
        line = f"#{t.id} ({t.priority}) {t.title}"
        if t.due:
            line += f" [due {t.due}]"
            if is_overdue(t, today):
                line += " OVERDUE"
            elif is_due_today(t, today):
                line += " DUE TODAY"
        lines.append(line)
    return lines


def toggle_selected_task(tasks: list[Task], index: int, today: date) -> bool:
    """Marks the task at `index` into the pending (not-done) task list --
    sorted the same way `task_lines` displays it -- done, reusing
    `complete_task`'s existing recurring-occurrence handling rather than
    duplicating it. Returns whether a task was actually toggled; `False`
    for an out-of-range index (an empty panel, or a stale selection left
    over from before the panel's contents changed) is a no-op rather
    than an error, since there's nothing destructive about ignoring it.
    """
    pending = _pending_tasks(tasks)
    if not 0 <= index < len(pending):
        return False
    complete_task(tasks, pending[index].id, today)
    return True


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


def check_in_selected_habit(habits: list[Habit], index: int, today: date) -> bool:
    """Checks in the habit at `index` -- `habit_lines` shows habits in
    the same order they're given, with no filtering or sorting, so the
    index lines up directly against `habits` -- reusing
    `check_in_habit`'s existing streak/grace-period logic rather than
    duplicating it. Returns whether a habit was actually checked in;
    `False` for an out-of-range index (an empty panel, or a stale
    selection) is a no-op rather than an error.
    """
    if not 0 <= index < len(habits):
        return False
    check_in_habit(habits[index], today)
    return True


def journal_lines(entries: list[Entry]) -> list[str]:
    if not entries:
        return ["No journal entries."]
    recent = list(reversed(entries))[:_JOURNAL_PANEL_LIMIT]
    lines = []
    for e in recent:
        first_line = e.body.splitlines()[0] if e.body else ""
        lines.append(f"#{e.id} [{e.created_at[:10]}] {first_line}")
    return lines


def build_journal_entry(entries: list[Entry], body: str) -> Entry | None:
    """Builds a new `Entry` from `body` -- already read back from the
    editor by the time this is called -- with the next available id,
    the same way the no-args `journal` command does. Returns `None`
    for an empty-after-stripping body, matching that command's existing
    "nothing to save" behavior, rather than saving a blank entry.
    """
    body = body.strip()
    if not body:
        return None
    next_id = max((e.id for e in entries), default=0) + 1
    return Entry(id=next_id, body=body)


def _task_line_colors(tasks: list[Task], today: str) -> list[str | None]:
    pending = _pending_tasks(tasks)
    if not pending:
        return [None]
    return [task_line_color(t, today) for t in pending]


def _habit_line_colors(habits: list[Habit], today: str) -> list[str | None]:
    if not habits:
        return [None]
    return [habit_line_color(h, today) for h in habits]


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
_ADD_KEYS = {ord("a"), ord("A")}


def handle_key(
    state: DashboardState, key: int, panel_lengths: tuple[int, int, int]
) -> tuple[DashboardState, str | None]:
    """Given the dashboard's current state, a curses keycode, and how
    many selectable items each panel currently has (tasks, habits,
    journal, in that order -- matching `PANELS`), returns the new state
    and an action: `"quit"`, `"activate"` (something should happen to
    whichever item is selected in the focused panel -- deciding what
    is items 71/72's job, not this function's, since no store is
    touched here), `"add"` (something new should be created in the
    focused panel -- so far only meaningful on the Journal panel, item
    76's job), or `None` for a key that was fully handled by just
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
    if key in _ADD_KEYS:
        return state, "add"
    return state, None


_SIDE_BY_SIDE_MIN_WIDTH = 100

_CURSES_COLOR = {
    "red": curses.COLOR_RED,
    "yellow": curses.COLOR_YELLOW,
    "blue": curses.COLOR_BLUE,
    "magenta": curses.COLOR_MAGENTA,
    "green": curses.COLOR_GREEN,
    "cyan": curses.COLOR_CYAN,
}


def _init_color_pairs() -> dict[str, int]:
    """Maps each color name `color.py`'s palette uses to a curses
    color-pair number, initialized once the screen is up -- `curses`
    has its own color mechanism (numbered pairs set with `init_pair`),
    not ANSI escapes, so the palette can't just be reused by calling
    `colorize()` and feeding the result to `addnstr`. Returns `{}`
    (meaning: don't color anything, exactly like the plain CLI output
    in the same situation) if `NO_COLOR` is set or the terminal doesn't
    support color at all -- the same two conditions `should_color()`
    checks for the regular commands.
    """
    if "NO_COLOR" in os.environ or not curses.has_colors():
        return {}
    curses.start_color()
    try:
        curses.use_default_colors()
        background = -1
    except curses.error:
        background = curses.COLOR_BLACK
    pairs = {}
    for number, name in enumerate(_CURSES_COLOR, start=1):
        curses.init_pair(number, _CURSES_COLOR[name], background)
        pairs[name] = number
    return pairs


def _draw_panel(
    win: curses.window,
    title: str,
    lines: list[str],
    line_colors: list[str | None],
    focused: bool,
    selected_index: int | None,
    color_pairs: dict[str, int],
) -> None:
    win.erase()
    win.border()
    height, width = win.getmaxyx()
    title_attr = curses.A_BOLD | curses.A_REVERSE if focused else curses.A_NORMAL
    win.addnstr(0, 2, f" {title} ", max(width - 4, 0), title_attr)
    for i, line in enumerate(lines[: max(height - 2, 0)]):
        line_attr = curses.A_REVERSE if i == selected_index else curses.A_NORMAL
        color_name = line_colors[i] if i < len(line_colors) else None
        if color_name is not None and color_name in color_pairs:
            line_attr |= curses.color_pair(color_pairs[color_name])
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


_MIN_HEIGHT = 12
_MIN_WIDTH = 20


def is_too_small(height: int, width: int) -> bool:
    """Below this, the three-panel layout stops being readable --
    `curses` itself doesn't error on a tinier window (`newwin` with a
    0 height/width is tolerated, just draws nothing useful), it just
    renders overlapping, unreadable borders, which is worse than a
    clear message since there's no error to see.
    """
    return height < _MIN_HEIGHT or width < _MIN_WIDTH


def too_small_message(height: int, width: int) -> str:
    return (
        f"Terminal too small for onepact ui "
        f"(need at least {_MIN_WIDTH}x{_MIN_HEIGHT}, got {width}x{height}). "
        "Resize it, or press q to quit."
    )


_PANEL_TITLES = ("Tasks", "Habits", "Journal")


def _read_journal_entry_suspending_curses(stdscr: curses.window) -> str:
    """Gives the real terminal back to `$EDITOR` for the duration of the
    call -- `curses` keeps its own idea of terminal state (raw mode, no
    echo, ...) that would otherwise fight with whatever the editor sets
    up -- then restores the dashboard's screen afterward. An editor
    that fails to launch at all (bad `$EDITOR`, etc.) is treated the
    same as an empty entry rather than crashing the dashboard.
    """
    curses.def_prog_mode()
    curses.endwin()
    try:
        body = read_entry_from_editor()
    except (OSError, subprocess.CalledProcessError):
        body = ""
    curses.reset_prog_mode()
    stdscr.refresh()
    return body


def _render(
    stdscr: curses.window,
    tasks: list[Task],
    habits: list[Habit],
    entries: list[Entry],
    today: str,
    save_tasks: Callable[[list[Task]], None],
    save_habits: Callable[[list[Habit]], None],
    save_entries: Callable[[list[Entry]], None],
) -> None:
    curses.curs_set(0)
    color_pairs = _init_color_pairs()
    state = DashboardState()
    while True:
        stdscr.erase()
        height, width = stdscr.getmaxyx()

        if is_too_small(height, width):
            stdscr.addnstr(0, 0, too_small_message(height, width), max(width, 0))
            stdscr.noutrefresh()
            curses.doupdate()
            key = stdscr.getch()
            if key in _QUIT_KEYS:
                return
            continue

        stdscr.noutrefresh()
        layout = _layout(height, width)

        panel_lines = (
            task_lines(tasks, today),
            habit_lines(habits, today),
            journal_lines(entries),
        )
        panel_colors: tuple[list[str | None], ...] = (
            _task_line_colors(tasks, today),
            _habit_line_colors(habits, today),
            [None] * len(panel_lines[2]),
        )
        panel_lengths = (
            sum(1 for t in tasks if not t.done),
            len(habits),
            min(len(entries), _JOURNAL_PANEL_LIMIT),
        )

        for i, ((win_height, win_width, y, x), title, lines, colors) in enumerate(
            zip(layout, _PANEL_TITLES, panel_lines, panel_colors)
        ):
            win = curses.newwin(win_height, win_width, y, x)
            focused = i == state.focus
            selected_index = state.selected[i] if focused else None
            _draw_panel(win, title, lines, colors, focused, selected_index, color_pairs)

        curses.doupdate()
        key = stdscr.getch()
        state, action = handle_key(state, key, panel_lengths)
        if action == "quit":
            return
        if action == "activate":
            today_date = date.fromisoformat(today)
            if state.focused_panel == "tasks":
                if toggle_selected_task(tasks, state.selected[0], today_date):
                    save_tasks(tasks)
            elif state.focused_panel == "habits":
                if check_in_selected_habit(habits, state.selected[1], today_date):
                    save_habits(habits)
        elif action == "add" and state.focused_panel == "journal":
            body = _read_journal_entry_suspending_curses(stdscr)
            entry = build_journal_entry(entries, body)
            if entry is not None:
                entries.append(entry)
                save_entries(entries)


def run(
    tasks: list[Task],
    habits: list[Habit],
    entries: list[Entry],
    today: str,
    save_tasks: Callable[[list[Task]], None],
    save_habits: Callable[[list[Habit]], None],
    save_entries: Callable[[list[Entry]], None],
) -> int:
    try:
        curses.wrapper(
            _render, tasks, habits, entries, today, save_tasks, save_habits, save_entries
        )
    except curses.error as exc:
        print(f"Could not start the terminal UI: {exc}", file=sys.stderr)
        return 1
    return 0
