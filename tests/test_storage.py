from kaizen.storage import Task, TaskStore, priority_rank


def test_task_defaults_to_med_priority():
    assert Task(id=1, title="a").priority == "med"


def test_from_dict_defaults_priority_when_missing():
    task = Task.from_dict({"id": 1, "title": "legacy task"})
    assert task.priority == "med"


def test_priority_rank_orders_high_first():
    assert priority_rank("high") < priority_rank("med") < priority_rank("low")


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
