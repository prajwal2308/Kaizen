import curses
from datetime import date

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


def test_task_line_color_matches_priority():
    assert ui.task_line_color(Task(id=1, title="a", priority="high"), "2026-01-10") == "red"
    assert ui.task_line_color(Task(id=1, title="a", priority="med"), "2026-01-10") == "yellow"
    assert ui.task_line_color(Task(id=1, title="a", priority="low"), "2026-01-10") == "blue"


def test_task_line_color_overdue_overrides_priority():
    task = Task(id=1, title="a", priority="low", due="2020-01-01")
    assert ui.task_line_color(task, "2026-01-10") == "red"


def test_habit_line_color_magenta_when_not_checked_in_today():
    habit = Habit(name="exercise", frequency="daily", last_checked="2026-01-09")
    assert ui.habit_line_color(habit, "2026-01-10") == "magenta"


def test_habit_line_color_green_when_checked_in_today():
    habit = Habit(name="exercise", frequency="daily", last_checked="2026-01-10")
    assert ui.habit_line_color(habit, "2026-01-10") == "green"


def test_toggle_selected_task_marks_the_task_at_that_index_done():
    tasks = [Task(id=1, title="only task")]
    assert ui.toggle_selected_task(tasks, 0, date(2026, 1, 10)) is True
    assert tasks[0].done is True
    assert tasks[0].done_at is not None


def test_toggle_selected_task_uses_the_same_order_as_task_lines():
    tasks = [
        Task(id=1, title="low", priority="low"),
        Task(id=2, title="high", priority="high"),
    ]
    # task_lines shows high-priority first, so index 0 is the high-priority task
    ui.toggle_selected_task(tasks, 0, date(2026, 1, 10))
    assert tasks[0].id == 1
    assert tasks[0].done is False
    assert tasks[1].id == 2
    assert tasks[1].done is True


def test_toggle_selected_task_skips_already_done_tasks_when_indexing():
    tasks = [
        Task(id=1, title="already done", done=True),
        Task(id=2, title="pending"),
    ]
    ui.toggle_selected_task(tasks, 0, date(2026, 1, 10))
    assert tasks[0].done is True
    assert tasks[1].done is True


def test_toggle_selected_task_out_of_range_index_is_a_no_op():
    tasks = [Task(id=1, title="only task")]
    assert ui.toggle_selected_task(tasks, 5, date(2026, 1, 10)) is False
    assert tasks[0].done is False


def test_toggle_selected_task_on_empty_list_is_a_no_op():
    assert ui.toggle_selected_task([], 0, date(2026, 1, 10)) is False


def test_toggle_selected_task_recurring_creates_next_occurrence():
    tasks = [Task(id=1, title="exercise", repeat="daily")]
    ui.toggle_selected_task(tasks, 0, date(2026, 1, 10))
    assert len(tasks) == 2
    assert tasks[1].due == "2026-01-11"
    assert tasks[1].done is False


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


def test_check_in_selected_habit_checks_in_the_habit_at_that_index():
    habits = [Habit(name="exercise", frequency="daily")]
    assert ui.check_in_selected_habit(habits, 0, date(2026, 1, 10)) is True
    assert habits[0].streak == 1
    assert habits[0].last_checked == "2026-01-10"


def test_check_in_selected_habit_uses_the_same_order_as_habit_lines():
    habits = [
        Habit(name="first", frequency="daily"),
        Habit(name="second", frequency="daily"),
    ]
    ui.check_in_selected_habit(habits, 1, date(2026, 1, 10))
    assert habits[0].streak == 0
    assert habits[1].streak == 1


def test_check_in_selected_habit_out_of_range_index_is_a_no_op():
    habits = [Habit(name="exercise", frequency="daily")]
    assert ui.check_in_selected_habit(habits, 5, date(2026, 1, 10)) is False
    assert habits[0].streak == 0


def test_check_in_selected_habit_on_empty_list_is_a_no_op():
    assert ui.check_in_selected_habit([], 0, date(2026, 1, 10)) is False


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


def test_init_color_pairs_empty_when_terminal_has_no_color_support(monkeypatch):
    monkeypatch.setattr(curses, "has_colors", lambda: False)
    assert ui._init_color_pairs() == {}


def test_init_color_pairs_empty_when_no_color_env_var_set(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setattr(curses, "has_colors", lambda: True)
    assert ui._init_color_pairs() == {}


def test_init_color_pairs_maps_every_palette_color_to_a_distinct_pair_number(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(curses, "has_colors", lambda: True)
    monkeypatch.setattr(curses, "start_color", lambda: None)
    monkeypatch.setattr(curses, "use_default_colors", lambda: None)
    registered = {}
    monkeypatch.setattr(
        curses, "init_pair", lambda number, fg, bg: registered.setdefault(number, (fg, bg))
    )

    pairs = ui._init_color_pairs()

    assert set(pairs) == {"red", "yellow", "blue", "magenta", "green", "cyan"}
    assert len(set(pairs.values())) == len(pairs)
    for name, number in pairs.items():
        assert registered[number] == (ui._CURSES_COLOR[name], -1)


def test_run_reports_curses_errors_instead_of_raising(monkeypatch, capsys):
    def fake_wrapper(func, *args):
        raise curses.error("nocbreak() returned ERR")

    monkeypatch.setattr(curses, "wrapper", fake_wrapper)

    assert (
        ui.run(
            [], [], [], "2026-01-10", save_tasks=lambda tasks: None, save_habits=lambda h: None
        )
        == 1
    )
    err = capsys.readouterr().err
    assert "Could not start the terminal UI" in err


def test_run_returns_zero_on_success(monkeypatch):
    monkeypatch.setattr(curses, "wrapper", lambda func, *args: None)
    assert (
        ui.run(
            [], [], [], "2026-01-10", save_tasks=lambda tasks: None, save_habits=lambda h: None
        )
        == 0
    )


def test_dashboard_state_defaults_to_tasks_focused():
    state = ui.DashboardState()
    assert state.focus == 0
    assert state.focused_panel == "tasks"
    assert state.selected == (0, 0, 0)


def test_handle_key_q_quits():
    state = ui.DashboardState()
    new_state, action = ui.handle_key(state, ord("q"), (3, 3, 3))
    assert action == "quit"
    assert new_state == state


def test_handle_key_capital_q_quits():
    state = ui.DashboardState()
    _, action = ui.handle_key(state, ord("Q"), (3, 3, 3))
    assert action == "quit"


def test_handle_key_tab_moves_focus_forward_and_wraps():
    state = ui.DashboardState()
    state, action = ui.handle_key(state, ord("\t"), (3, 3, 3))
    assert action is None
    assert state.focused_panel == "habits"

    state, _ = ui.handle_key(state, ord("\t"), (3, 3, 3))
    assert state.focused_panel == "journal"

    state, _ = ui.handle_key(state, ord("\t"), (3, 3, 3))
    assert state.focused_panel == "tasks"


def test_handle_key_shift_tab_moves_focus_backward_and_wraps():
    state = ui.DashboardState()
    state, action = ui.handle_key(state, curses.KEY_BTAB, (3, 3, 3))
    assert action is None
    assert state.focused_panel == "journal"


def test_handle_key_down_moves_selection_in_focused_panel_only():
    state = ui.DashboardState()
    state, action = ui.handle_key(state, curses.KEY_DOWN, (3, 3, 3))
    assert action is None
    assert state.selected == (1, 0, 0)


def test_handle_key_j_also_moves_selection_down():
    state = ui.DashboardState()
    state, _ = ui.handle_key(state, ord("j"), (3, 3, 3))
    assert state.selected == (1, 0, 0)


def test_handle_key_up_and_k_move_selection_up_and_wrap():
    state = ui.DashboardState()
    state, action = ui.handle_key(state, curses.KEY_UP, (3, 3, 3))
    assert action is None
    assert state.selected == (2, 0, 0)

    state, _ = ui.handle_key(state, ord("k"), (3, 3, 3))
    assert state.selected == (1, 0, 0)


def test_handle_key_down_wraps_to_zero_at_end_of_panel():
    state = ui.DashboardState(selected=(2, 0, 0))
    state, _ = ui.handle_key(state, curses.KEY_DOWN, (3, 3, 3))
    assert state.selected == (0, 0, 0)


def test_handle_key_selection_moves_in_whichever_panel_is_focused():
    state = ui.DashboardState(focus=1)
    state, _ = ui.handle_key(state, curses.KEY_DOWN, (3, 3, 3))
    assert state.selected == (0, 1, 0)
    assert state.focus == 1


def test_handle_key_selection_is_a_no_op_on_an_empty_panel():
    state = ui.DashboardState()
    state, action = ui.handle_key(state, curses.KEY_DOWN, (0, 3, 3))
    assert action is None
    assert state.selected == (0, 0, 0)


def test_handle_key_space_and_enter_return_activate():
    state = ui.DashboardState()
    _, action = ui.handle_key(state, ord(" "), (3, 3, 3))
    assert action == "activate"

    _, action = ui.handle_key(state, ord("\n"), (3, 3, 3))
    assert action == "activate"

    _, action = ui.handle_key(state, curses.KEY_ENTER, (3, 3, 3))
    assert action == "activate"


def test_handle_key_unrecognized_key_is_a_no_op():
    state = ui.DashboardState()
    new_state, action = ui.handle_key(state, ord("z"), (3, 3, 3))
    assert action is None
    assert new_state == state


class _FakeWindow:
    """Stands in for a real curses window so `_render`'s loop (state,
    action-handling, task mutation, save callback) can run under pytest
    -- only the handful of methods/attributes `_render`/`_draw_panel`
    actually call, none of which draw anything for real.
    """

    def __init__(self, height=50, width=120, keys=()):
        self._height = height
        self._width = width
        self.keys = list(keys)

    def erase(self):
        pass

    def noutrefresh(self):
        pass

    def getmaxyx(self):
        return (self._height, self._width)

    def border(self):
        pass

    def addnstr(self, *args, **kwargs):
        pass

    def getch(self):
        return self.keys.pop(0)


def test_render_activate_toggles_task_and_saves_through(monkeypatch):
    monkeypatch.setattr(curses, "curs_set", lambda n: None)
    monkeypatch.setattr(curses, "doupdate", lambda: None)
    monkeypatch.setattr(curses, "newwin", lambda h, w, y, x: _FakeWindow(h, w))
    monkeypatch.setattr(curses, "has_colors", lambda: False)

    tasks = [Task(id=1, title="only task")]
    stdscr = _FakeWindow(keys=[ord(" "), ord("q")])
    saved_tasks: list[list[Task]] = []

    ui._render(
        stdscr,
        tasks,
        [],
        [],
        "2026-01-10",
        save_tasks=saved_tasks.append,
        save_habits=lambda h: None,
    )

    assert tasks[0].done is True
    assert saved_tasks and saved_tasks[0][0].done is True


def test_render_activate_on_habits_panel_checks_in_habit_without_touching_tasks(monkeypatch):
    monkeypatch.setattr(curses, "curs_set", lambda n: None)
    monkeypatch.setattr(curses, "doupdate", lambda: None)
    monkeypatch.setattr(curses, "newwin", lambda h, w, y, x: _FakeWindow(h, w))
    monkeypatch.setattr(curses, "has_colors", lambda: False)

    tasks = [Task(id=1, title="only task")]
    habits = [Habit(name="exercise", frequency="daily")]
    # Tab moves focus to habits, then space checks in the selected habit.
    stdscr = _FakeWindow(keys=[ord("\t"), ord(" "), ord("q")])
    saved_tasks: list[list[Task]] = []
    saved_habits: list[list[Habit]] = []

    ui._render(
        stdscr,
        tasks,
        habits,
        [],
        "2026-01-10",
        save_tasks=saved_tasks.append,
        save_habits=saved_habits.append,
    )

    assert tasks[0].done is False
    assert saved_tasks == []
    assert habits[0].streak == 1
    assert saved_habits and saved_habits[0][0].streak == 1
