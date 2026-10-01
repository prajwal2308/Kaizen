from onepact.storage import (
    Entry,
    Habit,
    HabitStore,
    JournalStore,
    Task,
    TaskStore,
    is_overdue,
    priority_rank,
)


def test_task_defaults_to_med_priority():
    assert Task(id=1, title="a").priority == "med"


def test_from_dict_defaults_priority_when_missing():
    task = Task.from_dict({"id": 1, "title": "legacy task"})
    assert task.priority == "med"


def test_priority_rank_orders_high_first():
    assert priority_rank("high") < priority_rank("med") < priority_rank("low")


def test_task_due_defaults_to_none():
    assert Task(id=1, title="a").due is None


def test_from_dict_defaults_due_when_missing():
    task = Task.from_dict({"id": 1, "title": "legacy task"})
    assert task.due is None


def test_is_overdue_true_for_past_due_undone_task():
    task = Task(id=1, title="a", due="2026-01-01")
    assert is_overdue(task, today="2026-01-02") is True


def test_is_overdue_false_for_future_due_date():
    task = Task(id=1, title="a", due="2026-01-05")
    assert is_overdue(task, today="2026-01-02") is False


def test_is_overdue_false_when_done():
    task = Task(id=1, title="a", due="2026-01-01", done=True)
    assert is_overdue(task, today="2026-01-02") is False


def test_is_overdue_false_when_no_due_date():
    task = Task(id=1, title="a")
    assert is_overdue(task, today="2026-01-02") is False


def test_task_tags_defaults_to_empty_list():
    assert Task(id=1, title="a").tags == []


def test_from_dict_defaults_tags_when_missing():
    task = Task.from_dict({"id": 1, "title": "legacy task"})
    assert task.tags == []


def test_from_dict_reads_tags():
    task = Task.from_dict({"id": 1, "title": "a", "tags": ["work", "home"]})
    assert task.tags == ["work", "home"]


def test_task_tags_defaults_are_independent_instances():
    a = Task(id=1, title="a")
    b = Task(id=2, title="b")
    a.tags.append("work")
    assert b.tags == []


def test_task_repeat_defaults_to_none():
    assert Task(id=1, title="a").repeat is None


def test_from_dict_defaults_repeat_when_missing():
    task = Task.from_dict({"id": 1, "title": "legacy task"})
    assert task.repeat is None


def test_from_dict_reads_repeat():
    task = Task.from_dict({"id": 1, "title": "a", "repeat": "weekly"})
    assert task.repeat == "weekly"


def test_load_empty_when_no_file(tmp_path):
    store = TaskStore(data_dir=tmp_path)
    assert store.load() == []


def test_save_and_load_round_trip(tmp_path):
    store = TaskStore(data_dir=tmp_path)
    tasks = [Task(id=1, title="write tests"), Task(id=2, title="ship it", done=True)]
    store.save(tasks)

    loaded = store.load()

    assert [t.title for t in loaded] == ["write tests", "ship it"]
    assert loaded[1].done is True


def test_next_id_increments_from_max(tmp_path):
    store = TaskStore(data_dir=tmp_path)
    assert store.next_id([]) == 1
    assert store.next_id([Task(id=1, title="a"), Task(id=5, title="b")]) == 6


def test_entry_has_created_at_timestamp():
    entry = Entry(id=1, body="wrote some tests today")
    assert entry.created_at


def test_entry_from_dict_defaults_created_at_when_missing():
    entry = Entry.from_dict({"id": 1, "body": "legacy entry"})
    assert entry.created_at == ""


def test_entry_task_id_defaults_to_none():
    assert Entry(id=1, body="a").task_id is None


def test_entry_from_dict_defaults_task_id_when_missing():
    entry = Entry.from_dict({"id": 1, "body": "legacy entry"})
    assert entry.task_id is None


def test_entry_from_dict_reads_task_id():
    entry = Entry.from_dict({"id": 1, "body": "a", "task_id": 3})
    assert entry.task_id == 3


def test_journal_load_empty_when_no_file(tmp_path):
    store = JournalStore(data_dir=tmp_path)
    assert store.load() == []


def test_journal_save_and_load_round_trip(tmp_path):
    store = JournalStore(data_dir=tmp_path)
    entries = [Entry(id=1, body="first entry"), Entry(id=2, body="second entry")]
    store.save(entries)

    loaded = store.load()

    assert [e.body for e in loaded] == ["first entry", "second entry"]


def test_journal_next_id_increments_from_max(tmp_path):
    store = JournalStore(data_dir=tmp_path)
    assert store.next_id([]) == 1
    assert store.next_id([Entry(id=1, body="a"), Entry(id=5, body="b")]) == 6


def test_journal_store_is_independent_of_task_store(tmp_path):
    task_store = TaskStore(data_dir=tmp_path)
    journal_store = JournalStore(data_dir=tmp_path)
    task_store.save([Task(id=1, title="a task")])
    journal_store.save([Entry(id=1, body="an entry")])

    assert [t.title for t in task_store.load()] == ["a task"]
    assert [e.body for e in journal_store.load()] == ["an entry"]


def test_habit_streak_defaults_to_zero():
    assert Habit(name="exercise", frequency="daily").streak == 0


def test_habit_from_dict_defaults_streak_when_missing():
    habit = Habit.from_dict({"name": "exercise", "frequency": "daily"})
    assert habit.streak == 0


def test_habit_from_dict_reads_streak():
    habit = Habit.from_dict({"name": "exercise", "frequency": "daily", "streak": 7})
    assert habit.streak == 7


def test_habit_last_checked_defaults_to_none():
    assert Habit(name="exercise", frequency="daily").last_checked is None


def test_habit_from_dict_defaults_last_checked_when_missing():
    habit = Habit.from_dict({"name": "exercise", "frequency": "daily"})
    assert habit.last_checked is None


def test_habit_from_dict_reads_last_checked():
    habit = Habit.from_dict(
        {"name": "exercise", "frequency": "daily", "last_checked": "2026-09-30"}
    )
    assert habit.last_checked == "2026-09-30"


def test_habit_has_created_at_timestamp():
    assert Habit(name="exercise", frequency="daily").created_at


def test_habit_from_dict_defaults_created_at_when_missing():
    habit = Habit.from_dict({"name": "exercise", "frequency": "daily"})
    assert habit.created_at == ""


def test_habit_store_load_empty_when_no_file(tmp_path):
    store = HabitStore(data_dir=tmp_path)
    assert store.load() == []


def test_habit_store_save_and_load_round_trip(tmp_path):
    store = HabitStore(data_dir=tmp_path)
    habits = [
        Habit(name="exercise", frequency="daily", streak=3, last_checked="2026-09-30"),
        Habit(name="review inbox", frequency="weekly"),
    ]
    store.save(habits)

    loaded = store.load()

    assert [h.name for h in loaded] == ["exercise", "review inbox"]
    assert loaded[0].frequency == "daily"
    assert loaded[0].streak == 3
    assert loaded[0].last_checked == "2026-09-30"
    assert loaded[1].frequency == "weekly"
    assert loaded[1].streak == 0


def test_habit_store_is_independent_of_other_stores(tmp_path):
    task_store = TaskStore(data_dir=tmp_path)
    journal_store = JournalStore(data_dir=tmp_path)
    habit_store = HabitStore(data_dir=tmp_path)
    task_store.save([Task(id=1, title="a task")])
    journal_store.save([Entry(id=1, body="an entry")])
    habit_store.save([Habit(name="exercise", frequency="daily")])

    assert [t.title for t in task_store.load()] == ["a task"]
    assert [e.body for e in journal_store.load()] == ["an entry"]
    assert [h.name for h in habit_store.load()] == ["exercise"]
