from onepact.sqlite_storage import SqliteTaskStore
from onepact.storage import Task, TaskStore

# Mirrors tests/test_storage.py's TaskStore tests as closely as possible:
# SqliteTaskStore is meant to be a drop-in replacement, so its tests should
# prove the same behavior, not just "it works somehow".


def test_load_empty_when_no_file(tmp_path):
    store = SqliteTaskStore(data_dir=tmp_path)
    assert store.load() == []


def test_load_does_not_create_file(tmp_path):
    store = SqliteTaskStore(data_dir=tmp_path)
    store.load()
    assert not store.path.exists()


def test_save_and_load_round_trip(tmp_path):
    store = SqliteTaskStore(data_dir=tmp_path)
    tasks = [Task(id=1, title="write tests"), Task(id=2, title="ship it", done=True)]
    store.save(tasks)

    loaded = store.load()

    assert [t.title for t in loaded] == ["write tests", "ship it"]
    assert loaded[1].done is True


def test_next_id_increments_from_max(tmp_path):
    store = SqliteTaskStore(data_dir=tmp_path)
    assert store.next_id([]) == 1
    assert store.next_id([Task(id=1, title="a"), Task(id=5, title="b")]) == 6


def test_round_trip_preserves_all_task_fields(tmp_path):
    store = SqliteTaskStore(data_dir=tmp_path)
    task = Task(
        id=1,
        title="water the plants",
        created_at="2026-09-21T00:08:00+00:00",
        done=False,
        done_at=None,
        priority="high",
        due="2026-09-22",
        tags=["home", "urgent"],
        repeat="daily",
    )
    store.save([task])

    (loaded,) = store.load()
    assert loaded == task


def test_round_trip_preserves_done_task(tmp_path):
    store = SqliteTaskStore(data_dir=tmp_path)
    task = Task(
        id=1,
        title="finished task",
        done=True,
        done_at="2026-09-21T00:09:00+00:00",
    )
    store.save([task])

    (loaded,) = store.load()
    assert loaded.done is True
    assert loaded.done_at == "2026-09-21T00:09:00+00:00"


def test_round_trip_preserves_tag_order(tmp_path):
    store = SqliteTaskStore(data_dir=tmp_path)
    task = Task(id=1, title="a", tags=["zebra", "alpha", "middle"])
    store.save([task])

    (loaded,) = store.load()
    assert loaded.tags == ["zebra", "alpha", "middle"]


def test_task_without_tags_round_trips_to_empty_list(tmp_path):
    store = SqliteTaskStore(data_dir=tmp_path)
    store.save([Task(id=1, title="no tags")])

    (loaded,) = store.load()
    assert loaded.tags == []


def test_shared_tag_names_are_not_duplicated_across_tasks(tmp_path):
    store = SqliteTaskStore(data_dir=tmp_path)
    store.save(
        [
            Task(id=1, title="a", tags=["work"]),
            Task(id=2, title="b", tags=["work"]),
        ]
    )

    conn = store._connect()
    try:
        (tag_count,) = conn.execute("SELECT COUNT(*) FROM tags").fetchone()
    finally:
        conn.close()
    assert tag_count == 1


def test_save_overwrites_previous_contents(tmp_path):
    store = SqliteTaskStore(data_dir=tmp_path)
    store.save([Task(id=1, title="first save", tags=["work"])])

    store.save([Task(id=2, title="second save")])

    loaded = store.load()
    assert [t.title for t in loaded] == ["second save"]


def test_save_empty_list_clears_store(tmp_path):
    store = SqliteTaskStore(data_dir=tmp_path)
    store.save([Task(id=1, title="will be cleared")])

    store.save([])

    assert store.load() == []


def test_repeat_and_due_default_to_none_after_round_trip(tmp_path):
    store = SqliteTaskStore(data_dir=tmp_path)
    store.save([Task(id=1, title="bare task")])

    (loaded,) = store.load()
    assert loaded.due is None
    assert loaded.repeat is None


def test_load_orders_by_id(tmp_path):
    store = SqliteTaskStore(data_dir=tmp_path)
    store.save([Task(id=5, title="fifth"), Task(id=1, title="first")])

    loaded = store.load()
    assert [t.id for t in loaded] == [1, 5]


def test_matches_task_store_for_the_same_operation_sequence(tmp_path):
    """The real proof of 'same interface': run an identical sequence of
    load/next_id/save calls against both backends and compare results.
    """
    json_store = TaskStore(data_dir=tmp_path / "json")
    sqlite_store = SqliteTaskStore(data_dir=tmp_path / "sqlite")

    def add(store, title, **kwargs):
        tasks = store.load()
        tasks.append(Task(id=store.next_id(tasks), title=title, **kwargs))
        store.save(tasks)

    for store in (json_store, sqlite_store):
        add(store, "write tests", priority="high", tags=["work", "urgent"])
        add(store, "ship it", due="2026-09-22", repeat="weekly")
        add(store, "no-op task")

    # Mark the first task done and remove the third, on both backends.
    for store in (json_store, sqlite_store):
        tasks = store.load()
        tasks[0].done = True
        tasks[0].done_at = "2026-09-21T00:10:00+00:00"
        remaining = [t for t in tasks if t.id != tasks[2].id]
        store.save(remaining)

    json_tasks = json_store.load()
    sqlite_tasks = sqlite_store.load()
    # created_at is a real wall-clock timestamp captured independently by
    # each store's Task() calls above, so it legitimately differs by a few
    # microseconds between the two backends; everything else must match.
    for t in json_tasks + sqlite_tasks:
        t.created_at = ""
    assert json_tasks == sqlite_tasks
    assert sqlite_store.next_id(sqlite_tasks) == json_store.next_id(json_tasks)
