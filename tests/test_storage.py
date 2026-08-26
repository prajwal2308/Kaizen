from kaizen.storage import Task, TaskStore


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
