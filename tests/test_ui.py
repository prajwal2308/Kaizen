import curses

from onepact import ui
from onepact.storage import Entry, Habit, Task


def test_task_lines_empty():
    assert ui.task_lines([], "2026-01-10") == ["No tasks."]


def test_task_lines_excludes_done_tasks():
    tasks = [
        Task(id=1, title="pending", done=False),
        Task(id=2, title="finished", done=True),
    ]
    lines = ui.task_lines(tasks, "2026-01-10")
    assert lines == ["#1 (med) pending"]


def test_task_lines_sorted_by_priority_then_id():
    tasks = [
        Task(id=1, title="low prio", priority="low"),
        Task(id=2, title="high prio", priority="high"),
        Task(id=3, title="med prio", priority="med"),
    ]
    lines = ui.task_lines(tasks, "2026-01-10")
    assert [line.split(" ", 1)[0] for line in lines] == ["#2", "#3", "#1"]


def test_task_lines_shows_due_date_without_overdue_flag():
    tasks = [Task(id=1, title="due later", due="2099-01-01")]
    lines = ui.task_lines(tasks, "2026-01-10")
    assert lines == ["#1 (med) due later [due 2099-01-01]"]


def test_task_lines_flags_overdue():
    tasks = [Task(id=1, title="late task", due="2020-01-01")]
    lines = ui.task_lines(tasks, "2026-01-10")
    assert lines == ["#1 (med) late task [due 2020-01-01] OVERDUE"]


def test_habit_lines_empty():
    assert ui.habit_lines([], "2026-01-10") == ["No habits."]


def test_habit_lines_shows_streak():
    habits = [Habit(name="exercise", frequency="daily", streak=5)]
    lines = ui.habit_lines(habits, "2026-01-10")
    assert lines == ["exercise [daily] streak:5"]


def test_habit_lines_flags_checked_in_today():
    habits = [
        Habit(name="exercise", frequency="daily", streak=5, last_checked="2026-01-10")
    ]
    lines = ui.habit_lines(habits, "2026-01-10")
    assert lines == ["exercise [daily] streak:5 (checked in today)"]


def test_habit_lines_does_not_flag_when_not_checked_today():
    habits = [
        Habit(name="exercise", frequency="daily", streak=5, last_checked="2026-01-09")
    ]
    lines = ui.habit_lines(habits, "2026-01-10")
    assert lines == ["exercise [daily] streak:5"]


def test_journal_lines_empty():
    assert ui.journal_lines([]) == ["No journal entries."]


def test_journal_lines_most_recent_first():
    entries = [
        Entry(id=1, created_at="2026-01-01T00:00:00+00:00", body="first"),
        Entry(id=2, created_at="2026-01-02T00:00:00+00:00", body="second"),
    ]
    lines = ui.journal_lines(entries)
    assert lines == ["#2 [2026-01-02] second", "#1 [2026-01-01] first"]


def test_journal_lines_shows_only_first_line_of_body():
    entries = [
        Entry(id=1, created_at="2026-01-01T00:00:00+00:00", body="first line\nsecond line")
    ]
    lines = ui.journal_lines(entries)
    assert lines == ["#1 [2026-01-01] first line"]


def test_journal_lines_capped_at_five():
    entries = [
        Entry(id=i, created_at=f"2026-01-{i:02d}T00:00:00+00:00", body=f"entry {i}")
        for i in range(1, 8)
    ]
    lines = ui.journal_lines(entries)
    assert len(lines) == 5
    assert lines[0] == "#7 [2026-01-07] entry 7"


def test_layout_side_by_side_on_wide_terminal():
    layout = ui._layout(height=40, width=120)
    assert len(layout) == 3
    heights = {h for h, _, _, _ in layout}
    assert heights == {40}
    widths = [w for _, w, _, _ in layout]
    assert sum(widths) == 120
    xs = [x for _, _, _, x in layout]
    assert xs == [0, widths[0], widths[0] + widths[1]]


def test_layout_stacked_on_narrow_terminal():
    layout = ui._layout(height=30, width=80)
    assert len(layout) == 3
    widths = {w for _, w, _, _ in layout}
    assert widths == {80}
    heights = [h for h, _, _, _ in layout]
    assert sum(heights) == 30
    ys = [y for _, _, y, _ in layout]
    assert ys == [0, heights[0], heights[0] + heights[1]]


def test_run_reports_curses_errors_instead_of_raising(monkeypatch, capsys):
    def fake_wrapper(func, *args):
        raise curses.error("nocbreak() returned ERR")

    monkeypatch.setattr(curses, "wrapper", fake_wrapper)

    assert ui.run([], [], [], "2026-01-10") == 1
    err = capsys.readouterr().err
    assert "Could not start the terminal UI" in err


def test_run_returns_zero_on_success(monkeypatch):
    monkeypatch.setattr(curses, "wrapper", lambda func, *args: None)
    assert ui.run([], [], [], "2026-01-10") == 0
