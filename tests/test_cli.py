import csv
import io
import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from onepact.cli import _read_entry_from_editor, main
from onepact.config import load_config, set_config_value
from onepact.sqlite_storage import SqliteTaskStore
from onepact.storage import JournalStore, Task, TaskStore


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr("onepact.cli.TaskStore", lambda: TaskStore(data_dir=tmp_path))
    monkeypatch.setattr("onepact.cli.JournalStore", lambda: JournalStore(data_dir=tmp_path))
    # Existing tests target the JSON store directly (e.g. TaskStore(data_dir=tmp_path).load()
    # below), so force backend="json" here regardless of the real default -- this is the
    # "keep JSON store for tests/back-compat" half of switching the CLI's default backend
    # to sqlite. Tests that specifically exercise sqlite-default behavior re-patch
    # onepact.cli.load_config themselves to the unmodified function.
    monkeypatch.setattr(
        "onepact.cli.load_config",
        lambda: {**load_config(data_dir=tmp_path), "backend": "json"},
    )
    monkeypatch.setattr(
        "onepact.cli.set_config_value",
        lambda key, value: set_config_value(key, value, data_dir=tmp_path),
    )
    monkeypatch.setattr(
        "onepact.cli.SqliteTaskStore", lambda: SqliteTaskStore(data_dir=tmp_path)
    )


def test_add_and_list(capsys):
    assert main(["add", "buy milk"]) == 0
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "buy milk" in out


def test_done_hides_from_default_list(capsys):
    main(["add", "task one"])
    main(["done", "1"])
    capsys.readouterr()

    main(["list"])
    assert "task one" not in capsys.readouterr().out

    main(["list", "--all"])
    assert "task one" in capsys.readouterr().out


def test_done_unknown_id_errors():
    assert main(["done", "999"]) == 1


def test_done_daily_recurring_creates_next_occurrence(capsys, tmp_path):
    main(["add", "water the plants", "--repeat", "daily", "--priority", "high"])
    capsys.readouterr()

    assert main(["done", "1"]) == 0
    out = capsys.readouterr().out
    assert "Marked #1 done." in out
    assert "Created #2: water the plants" in out
    assert "(next daily occurrence)" in out

    today = datetime.now(timezone.utc).date()
    expected_due = (today + timedelta(days=1)).isoformat()
    tasks = TaskStore(data_dir=tmp_path).load()
    assert len(tasks) == 2
    next_task = tasks[1]
    assert next_task.title == "water the plants"
    assert next_task.priority == "high"
    assert next_task.repeat == "daily"
    assert next_task.due == expected_due
    assert next_task.done is False


def test_done_weekly_recurring_creates_next_occurrence(tmp_path):
    main(["add", "take out recycling", "--repeat", "weekly"])

    assert main(["done", "1"]) == 0

    today = datetime.now(timezone.utc).date()
    expected_due = (today + timedelta(days=7)).isoformat()
    tasks = TaskStore(data_dir=tmp_path).load()
    assert len(tasks) == 2
    assert tasks[1].due == expected_due
    assert tasks[1].repeat == "weekly"


def test_done_recurring_preserves_tags(tmp_path):
    main(["add", "standup", "--repeat", "daily", "--tag", "work", "--tag", "team"])

    main(["done", "1"])

    tasks = TaskStore(data_dir=tmp_path).load()
    assert tasks[1].tags == ["work", "team"]


def test_done_non_recurring_task_creates_no_next_occurrence(capsys, tmp_path):
    main(["add", "one-off task"])
    capsys.readouterr()

    assert main(["done", "1"]) == 0
    out = capsys.readouterr().out
    assert "Created #" not in out

    tasks = TaskStore(data_dir=tmp_path).load()
    assert len(tasks) == 1


def test_done_recurring_marks_original_done_and_keeps_repeat(tmp_path):
    main(["add", "water the plants", "--repeat", "daily"])

    main(["done", "1"])

    tasks = TaskStore(data_dir=tmp_path).load()
    original = tasks[0]
    assert original.done is True
    assert original.done_at is not None
    assert original.repeat == "daily"


def test_done_recurring_chains_across_multiple_completions(tmp_path):
    main(["add", "daily habit", "--repeat", "daily"])

    main(["done", "1"])
    main(["done", "2"])

    tasks = TaskStore(data_dir=tmp_path).load()
    assert len(tasks) == 3
    assert [t.done for t in tasks] == [True, True, False]
    assert tasks[2].title == "daily habit"
    assert tasks[2].repeat == "daily"


def test_add_default_priority_is_med(capsys):
    main(["add", "no priority given"])
    main(["list"])
    out = capsys.readouterr().out
    assert "(med) no priority given" in out


def test_add_uses_config_default_priority(capsys, tmp_path):
    (tmp_path / "config.toml").write_text('priority = "high"\n')

    main(["add", "task with config default"])
    main(["list"])
    out = capsys.readouterr().out
    assert "(high) task with config default" in out


def test_add_explicit_priority_overrides_config(tmp_path):
    (tmp_path / "config.toml").write_text('priority = "high"\n')

    main(["add", "explicit wins", "--priority", "low"])

    tasks = TaskStore(data_dir=tmp_path).load()
    assert tasks[0].priority == "low"


def test_config_show_default(capsys):
    assert main(["config", "show"]) == 0
    out = capsys.readouterr().out
    assert "priority = med" in out


def test_config_show_reflects_file(capsys, tmp_path):
    (tmp_path / "config.toml").write_text('priority = "high"\n')

    main(["config", "show"])
    out = capsys.readouterr().out
    assert "priority = high" in out


def test_config_show_includes_unknown_keys_from_file(capsys, tmp_path):
    (tmp_path / "config.toml").write_text('priority = "high"\nmystery = "value"\n')

    main(["config", "show"])
    out = capsys.readouterr().out
    assert "priority = high" in out
    assert "mystery = value" in out


def test_config_set_preserves_other_keys_via_cli(tmp_path):
    (tmp_path / "config.toml").write_text('mystery = "kept"\npriority = "low"\n')

    main(["config", "set", "priority", "high"])

    text = (tmp_path / "config.toml").read_text()
    assert 'mystery = "kept"' in text
    assert 'priority = "high"' in text


def test_config_set_updates_value(capsys, tmp_path):
    assert main(["config", "set", "priority", "high"]) == 0
    out = capsys.readouterr().out
    assert "Set priority = high" in out

    main(["config", "show"])
    out = capsys.readouterr().out
    assert "priority = high" in out


def test_config_set_then_add_uses_new_default(tmp_path):
    main(["config", "set", "priority", "high"])

    main(["add", "task after config set"])

    tasks = TaskStore(data_dir=tmp_path).load()
    assert tasks[0].priority == "high"


def test_config_set_unknown_key_errors(capsys):
    assert main(["config", "set", "bogus", "value"]) == 1
    err = capsys.readouterr().err
    assert "Unknown config key" in err


def test_config_set_invalid_priority_value_errors(capsys, tmp_path):
    assert main(["config", "set", "priority", "urgent"]) == 1
    err = capsys.readouterr().err
    assert "Invalid value" in err
    assert not (tmp_path / "config.toml").exists()


def test_migrate_json_to_sqlite_copies_tasks(capsys, tmp_path):
    main(["add", "write tests", "--priority", "high", "--tag", "work"])
    main(["add", "ship it", "--due", "2026-09-22", "--repeat", "weekly"])
    capsys.readouterr()

    assert main(["migrate", "json-to-sqlite"]) == 0
    out = capsys.readouterr().out
    assert "Migrated 2 task(s)" in out

    sqlite_tasks = SqliteTaskStore(data_dir=tmp_path).load()
    json_tasks = TaskStore(data_dir=tmp_path).load()
    assert [t.title for t in sqlite_tasks] == ["write tests", "ship it"]
    assert sqlite_tasks[0].priority == "high"
    assert sqlite_tasks[0].tags == ["work"]
    assert sqlite_tasks[1].repeat == "weekly"
    # The JSON store is untouched -- this is a copy, not a move.
    assert [t.title for t in json_tasks] == ["write tests", "ship it"]


def test_migrate_json_to_sqlite_handles_empty_store(capsys):
    assert main(["migrate", "json-to-sqlite"]) == 0
    out = capsys.readouterr().out
    assert "Migrated 0 task(s)" in out


def test_migrate_refuses_to_overwrite_existing_sqlite_data(capsys, tmp_path):
    main(["add", "original json task"])
    capsys.readouterr()
    SqliteTaskStore(data_dir=tmp_path).save(
        [Task(id=99, title="already migrated task")]
    )

    assert main(["migrate", "json-to-sqlite"]) == 1
    err = capsys.readouterr().err
    assert "already has 1 task(s)" in err

    sqlite_tasks = SqliteTaskStore(data_dir=tmp_path).load()
    assert [t.title for t in sqlite_tasks] == ["already migrated task"]


def test_migrate_invalid_direction_errors():
    with pytest.raises(SystemExit):
        main(["migrate", "sqlite-to-json"])


def _use_real_backend_default(monkeypatch, tmp_path):
    """Undoes the autouse fixture's forced backend="json" for a single test,
    so `add`/`list`/etc. exercise whatever backend config.py actually
    defaults to (sqlite).
    """
    monkeypatch.setattr("onepact.cli.load_config", lambda: load_config(data_dir=tmp_path))


def test_default_backend_is_sqlite_when_unconfigured(capsys, tmp_path, monkeypatch):
    _use_real_backend_default(monkeypatch, tmp_path)

    main(["add", "stored in sqlite"])
    main(["list"])
    out = capsys.readouterr().out
    assert "stored in sqlite" in out

    assert SqliteTaskStore(data_dir=tmp_path).path.exists()
    assert not TaskStore(data_dir=tmp_path).path.exists()


def test_config_set_backend_json_switches_back_to_json_store(capsys, tmp_path, monkeypatch):
    _use_real_backend_default(monkeypatch, tmp_path)
    set_config_value("backend", "json", data_dir=tmp_path)

    main(["add", "stored in json"])
    main(["list"])
    out = capsys.readouterr().out
    assert "stored in json" in out

    assert TaskStore(data_dir=tmp_path).path.exists()
    assert not SqliteTaskStore(data_dir=tmp_path).path.exists()


def test_sqlite_backend_auto_migrates_existing_json_tasks(capsys, tmp_path, monkeypatch):
    main(["add", "already in json", "--priority", "high", "--tag", "work"])
    capsys.readouterr()

    _use_real_backend_default(monkeypatch, tmp_path)
    main(["list"])
    out = capsys.readouterr().out
    assert "already in json" in out

    sqlite_tasks = SqliteTaskStore(data_dir=tmp_path).load()
    assert [t.title for t in sqlite_tasks] == ["already in json"]
    assert sqlite_tasks[0].priority == "high"
    assert sqlite_tasks[0].tags == ["work"]
    # A copy, not a move -- the JSON file is untouched.
    json_tasks = TaskStore(data_dir=tmp_path).load()
    assert [t.title for t in json_tasks] == ["already in json"]


def test_sqlite_backend_does_not_re_migrate_once_db_exists(tmp_path, monkeypatch):
    main(["add", "original"])
    _use_real_backend_default(monkeypatch, tmp_path)
    main(["list"])  # triggers the one-time auto-migration

    # A task added directly to the JSON store afterwards should not appear --
    # the sqlite db already exists, so it's no longer auto-migrated from.
    tasks = TaskStore(data_dir=tmp_path).load()
    tasks.append(Task(id=2, title="added to json after migration"))
    TaskStore(data_dir=tmp_path).save(tasks)

    sqlite_tasks = SqliteTaskStore(data_dir=tmp_path).load()
    assert [t.title for t in sqlite_tasks] == ["original"]


def test_migrate_command_ignores_backend_config(capsys, tmp_path):
    (tmp_path / "config.toml").write_text('backend = "sqlite"\n')
    main(["add", "json task"])
    capsys.readouterr()

    assert main(["migrate", "json-to-sqlite"]) == 0
    out = capsys.readouterr().out
    assert "Migrated 1 task(s)" in out
    assert [t.title for t in TaskStore(data_dir=tmp_path).load()] == ["json task"]


def test_journal_task_link_checks_active_backend(capsys, tmp_path, monkeypatch):
    _use_real_backend_default(monkeypatch, tmp_path)
    main(["add", "task in sqlite"])
    capsys.readouterr()

    assert main(["journal", "note about it", "--task", "1"]) == 0
    out = capsys.readouterr().out
    assert "linked to task #1" in out

    assert main(["journal", "bad link", "--task", "999"]) == 1
    err = capsys.readouterr().err
    assert "No task with id 999" in err


def test_config_set_backend_rejects_invalid_value(capsys):
    assert main(["config", "set", "backend", "xml"]) == 1
    err = capsys.readouterr().err
    assert "Invalid value 'xml' for 'backend'" in err


def test_config_set_backend_accepts_sqlite(tmp_path):
    main(["config", "set", "backend", "sqlite"])
    text = (tmp_path / "config.toml").read_text()
    assert 'backend = "sqlite"' in text


def test_export_json_to_stdout(capsys):
    main(["add", "write tests", "--priority", "high", "--tag", "work", "--tag", "urgent"])
    main(["add", "ship it", "--due", "2026-09-22", "--repeat", "weekly"])
    main(["done", "1"])
    capsys.readouterr()

    assert main(["export", "--format", "json"]) == 0
    out = capsys.readouterr().out
    tasks = json.loads(out)
    assert [t["title"] for t in tasks] == ["write tests", "ship it"]
    assert tasks[0]["priority"] == "high"
    assert tasks[0]["tags"] == ["work", "urgent"]
    assert tasks[0]["done"] is True
    assert tasks[0]["done_at"] is not None
    assert tasks[1]["due"] == "2026-09-22"
    assert tasks[1]["repeat"] == "weekly"


def test_export_json_empty_store(capsys):
    assert main(["export", "--format", "json"]) == 0
    out = capsys.readouterr().out
    assert json.loads(out) == []


def test_export_csv_to_stdout(capsys):
    main(["add", "write tests", "--priority", "high", "--tag", "work", "--tag", "urgent"])
    main(["add", "ship it", "--due", "2026-09-22", "--repeat", "weekly"])
    main(["done", "1"])
    capsys.readouterr()

    assert main(["export", "--format", "csv"]) == 0
    out = capsys.readouterr().out
    rows = list(csv.reader(io.StringIO(out)))
    assert rows[0] == [
        "id", "title", "priority", "due", "done", "done_at", "created_at", "tags", "repeat",
    ]
    assert rows[1][0:5] == ["1", "write tests", "high", "", "true"]
    assert rows[1][7] == "work;urgent"
    assert rows[2][0:5] == ["2", "ship it", "med", "2026-09-22", "false"]
    assert rows[2][8] == "weekly"


def test_export_csv_empty_store(capsys):
    assert main(["export", "--format", "csv"]) == 0
    out = capsys.readouterr().out
    rows = list(csv.reader(io.StringIO(out)))
    assert len(rows) == 1
    assert rows[0][0] == "id"


def test_export_json_to_file(capsys, tmp_path):
    main(["add", "write tests"])
    capsys.readouterr()

    out_file = tmp_path / "export.json"
    assert main(["export", "--format", "json", "--output", str(out_file)]) == 0
    msg = capsys.readouterr().out
    assert f"Exported 1 task(s) to {out_file}" in msg

    tasks = json.loads(out_file.read_text())
    assert [t["title"] for t in tasks] == ["write tests"]


def test_export_csv_to_file(capsys, tmp_path):
    main(["add", "write tests"])
    capsys.readouterr()

    out_file = tmp_path / "export.csv"
    assert main(["export", "--format", "csv", "-o", str(out_file)]) == 0
    msg = capsys.readouterr().out
    assert f"Exported 1 task(s) to {out_file}" in msg

    rows = list(csv.reader(io.StringIO(out_file.read_text())))
    assert rows[1][1] == "write tests"


def test_export_requires_format():
    with pytest.raises(SystemExit):
        main(["export"])


def test_export_rejects_invalid_format():
    with pytest.raises(SystemExit):
        main(["export", "--format", "xml"])


def test_export_reads_from_active_backend(capsys, tmp_path, monkeypatch):
    _use_real_backend_default(monkeypatch, tmp_path)
    main(["add", "stored in sqlite"])
    capsys.readouterr()

    assert main(["export", "--format", "json"]) == 0
    tasks = json.loads(capsys.readouterr().out)
    assert [t["title"] for t in tasks] == ["stored in sqlite"]


def test_import_json_round_trips_with_export(capsys, tmp_path):
    main(["add", "write tests", "--priority", "high", "--tag", "work", "--tag", "urgent"])
    main(["add", "ship it", "--due", "2026-09-22", "--repeat", "weekly"])
    main(["done", "1"])
    capsys.readouterr()

    export_file = tmp_path / "export.json"
    main(["export", "--format", "json", "--output", str(export_file)])
    original = TaskStore(data_dir=tmp_path).load()

    # Clear the store, then import the export back in.
    TaskStore(data_dir=tmp_path).save([])
    capsys.readouterr()

    assert main(["import", str(export_file)]) == 0
    out = capsys.readouterr().out
    assert f"Imported 2 task(s) from {export_file}" in out

    imported = TaskStore(data_dir=tmp_path).load()
    assert len(imported) == 2
    for orig, got in zip(original, imported):
        assert got.title == orig.title
        assert got.priority == orig.priority
        assert got.due == orig.due
        assert got.tags == orig.tags
        assert got.repeat == orig.repeat
        assert got.done == orig.done
        assert got.done_at == orig.done_at
        assert got.created_at == orig.created_at


def test_import_csv_round_trips_with_export(capsys, tmp_path):
    main(["add", "write tests", "--priority", "high", "--tag", "work", "--tag", "urgent"])
    main(["add", "ship it", "--due", "2026-09-22", "--repeat", "weekly"])
    main(["done", "1"])
    capsys.readouterr()

    export_file = tmp_path / "export.csv"
    main(["export", "--format", "csv", "--output", str(export_file)])
    original = TaskStore(data_dir=tmp_path).load()

    TaskStore(data_dir=tmp_path).save([])
    capsys.readouterr()

    assert main(["import", str(export_file)]) == 0
    imported = TaskStore(data_dir=tmp_path).load()
    assert len(imported) == 2
    for orig, got in zip(original, imported):
        assert got.title == orig.title
        assert got.priority == orig.priority
        assert got.due == orig.due
        assert got.tags == orig.tags
        assert got.repeat == orig.repeat
        assert got.done == orig.done
        assert got.done_at == orig.done_at


def test_import_infers_format_from_extension(tmp_path):
    (tmp_path / "data.json").write_text(json.dumps([{"id": 1, "title": "from json ext"}]))
    main(["import", str(tmp_path / "data.json")])
    tasks = TaskStore(data_dir=tmp_path).load()
    assert [t.title for t in tasks] == ["from json ext"]


def test_import_format_flag_overrides_extension(tmp_path):
    (tmp_path / "data.txt").write_text(json.dumps([{"id": 1, "title": "from txt override"}]))
    main(["import", str(tmp_path / "data.txt"), "--format", "json"])
    tasks = TaskStore(data_dir=tmp_path).load()
    assert [t.title for t in tasks] == ["from txt override"]


def test_import_unknown_extension_without_format_errors(capsys, tmp_path):
    data_file = tmp_path / "data.txt"
    data_file.write_text("[]")
    assert main(["import", str(data_file)]) == 1
    err = capsys.readouterr().err
    assert "Cannot infer format" in err


def test_import_missing_file_errors(capsys, tmp_path):
    missing = tmp_path / "missing.json"
    assert main(["import", str(missing)]) == 1
    err = capsys.readouterr().err
    assert f"No such file: {missing}" in err


def test_import_malformed_json_errors(capsys, tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not json")
    assert main(["import", str(bad_file)]) == 1
    err = capsys.readouterr().err
    assert f"Could not parse {bad_file} as json" in err


def test_import_appends_to_existing_tasks_with_new_ids(tmp_path):
    main(["add", "already here"])
    export_file = tmp_path / "export.json"
    main(["export", "--format", "json", "--output", str(export_file)])

    main(["import", str(export_file)])

    tasks = TaskStore(data_dir=tmp_path).load()
    assert [t.title for t in tasks] == ["already here", "already here"]
    assert [t.id for t in tasks] == [1, 2]


def test_import_json_missing_optional_fields_uses_defaults(tmp_path):
    (tmp_path / "minimal.json").write_text(json.dumps([{"id": 1, "title": "bare minimum"}]))
    main(["import", str(tmp_path / "minimal.json")])
    tasks = TaskStore(data_dir=tmp_path).load()
    assert tasks[0].priority == "med"
    assert tasks[0].done is False
    assert tasks[0].tags == []


def test_import_writes_to_active_backend(capsys, tmp_path, monkeypatch):
    export_file = tmp_path / "export.json"
    export_file.write_text(json.dumps([{"id": 1, "title": "goes to sqlite"}]))

    _use_real_backend_default(monkeypatch, tmp_path)
    assert main(["import", str(export_file)]) == 0

    tasks = SqliteTaskStore(data_dir=tmp_path).load()
    assert [t.title for t in tasks] == ["goes to sqlite"]


def test_add_with_priority_shown_in_list(capsys):
    main(["add", "fix the outage", "--priority", "high"])
    main(["list"])
    out = capsys.readouterr().out
    assert "(high) fix the outage" in out


def test_list_sorts_by_priority_high_first(capsys):
    main(["add", "low task", "--priority", "low"])
    main(["add", "high task", "--priority", "high"])
    main(["add", "med task", "--priority", "med"])
    capsys.readouterr()

    main(["list"])
    out = capsys.readouterr().out
    assert out.index("high task") < out.index("med task") < out.index("low task")


def test_list_sort_priority_is_the_default(capsys):
    main(["add", "low task", "--priority", "low"])
    main(["add", "high task", "--priority", "high"])
    capsys.readouterr()

    main(["list", "--sort", "priority"])
    out = capsys.readouterr().out
    assert out.index("high task") < out.index("low task")


def test_list_sort_due_earliest_first(capsys):
    main(["add", "due later", "--due", "2026-12-01"])
    main(["add", "due sooner", "--due", "2026-10-01"])
    main(["add", "no due date"])
    capsys.readouterr()

    main(["list", "--sort", "due"])
    out = capsys.readouterr().out
    assert out.index("due sooner") < out.index("due later") < out.index("no due date")


def test_list_sort_created_oldest_first(capsys):
    main(["add", "created first"])
    main(["add", "created second"])
    main(["add", "created third"])
    capsys.readouterr()

    main(["list", "--sort", "created"])
    out = capsys.readouterr().out
    assert out.index("created first") < out.index("created second") < out.index("created third")


def test_list_sort_invalid_choice_errors():
    with pytest.raises(SystemExit):
        main(["list", "--sort", "bogus"])


def test_list_overdue_shows_only_overdue_tasks(capsys):
    main(["add", "past due", "--due", "2000-01-01"])
    main(["add", "future due", "--due", "2099-01-01"])
    main(["add", "no due date"])
    capsys.readouterr()

    main(["list", "--overdue"])
    out = capsys.readouterr().out
    assert "past due" in out
    assert "future due" not in out
    assert "no due date" not in out


def test_list_overdue_excludes_done_tasks(capsys):
    main(["add", "past due", "--due", "2000-01-01"])
    main(["done", "1"])
    capsys.readouterr()

    main(["list", "--overdue"])
    out = capsys.readouterr().out
    assert "No tasks." in out


def test_list_overdue_no_matches(capsys):
    main(["add", "future due", "--due", "2099-01-01"])
    capsys.readouterr()

    assert main(["list", "--overdue"]) == 0
    out = capsys.readouterr().out
    assert "No tasks." in out


def test_list_overdue_combines_with_tag(capsys):
    main(["add", "overdue work task", "--due", "2000-01-01", "--tag", "work"])
    main(["add", "overdue home task", "--due", "2000-01-01", "--tag", "home"])
    capsys.readouterr()

    main(["list", "--overdue", "--tag", "work"])
    out = capsys.readouterr().out
    assert "overdue work task" in out
    assert "overdue home task" not in out


def test_list_filters_by_priority(capsys):
    main(["add", "high task", "--priority", "high"])
    main(["add", "low task", "--priority", "low"])
    capsys.readouterr()

    main(["list", "--priority", "high"])
    out = capsys.readouterr().out
    assert "high task" in out
    assert "low task" not in out


def test_list_combines_tag_and_priority(capsys):
    main(["add", "work high", "--priority", "high", "--tag", "work"])
    main(["add", "work low", "--priority", "low", "--tag", "work"])
    main(["add", "home high", "--priority", "high", "--tag", "home"])
    capsys.readouterr()

    main(["list", "--tag", "work", "--priority", "high"])
    out = capsys.readouterr().out
    assert "work high" in out
    assert "work low" not in out
    assert "home high" not in out


def test_list_priority_invalid_choice_errors():
    with pytest.raises(SystemExit):
        main(["list", "--priority", "urgent"])


def test_list_overdue_combines_with_priority(capsys):
    main(["add", "overdue high", "--due", "2000-01-01", "--priority", "high"])
    main(["add", "overdue low", "--due", "2000-01-01", "--priority", "low"])
    capsys.readouterr()

    main(["list", "--overdue", "--priority", "high"])
    out = capsys.readouterr().out
    assert "overdue high" in out
    assert "overdue low" not in out


def test_list_combines_tag_priority_and_overdue(capsys):
    main(["add", "match", "--due", "2000-01-01", "--priority", "high", "--tag", "work"])
    main(["add", "wrong priority", "--due", "2000-01-01", "--priority", "low", "--tag", "work"])
    main(["add", "wrong tag", "--due", "2000-01-01", "--priority", "high", "--tag", "home"])
    main(["add", "not overdue", "--due", "2099-01-01", "--priority", "high", "--tag", "work"])
    capsys.readouterr()

    main(["list", "--tag", "work", "--priority", "high", "--overdue"])
    out = capsys.readouterr().out
    assert "match" in out
    assert "wrong priority" not in out
    assert "wrong tag" not in out
    assert "not overdue" not in out


def test_list_sort_applies_after_overdue_filter(capsys):
    main(["add", "overdue later", "--due", "2000-01-05"])
    main(["add", "overdue sooner", "--due", "2000-01-01"])
    main(["add", "not overdue", "--due", "2099-01-01"])
    capsys.readouterr()

    main(["list", "--overdue", "--sort", "due"])
    out = capsys.readouterr().out
    assert "not overdue" not in out
    assert out.index("overdue sooner") < out.index("overdue later")


def test_list_sort_due_with_all_undated_tasks_orders_by_id(capsys):
    main(["add", "first"])
    main(["add", "second"])
    main(["add", "third"])
    capsys.readouterr()

    main(["list", "--sort", "due"])
    out = capsys.readouterr().out
    assert out.index("first") < out.index("second") < out.index("third")


def test_add_with_due_shown_in_list(capsys):
    main(["add", "renew passport", "--due", "2099-01-01"])
    main(["list"])
    out = capsys.readouterr().out
    assert "[due 2099-01-01]" in out
    assert "OVERDUE" not in out


def test_list_marks_past_due_task_overdue(capsys):
    main(["add", "pay rent", "--due", "2000-01-01"])
    main(["list"])
    out = capsys.readouterr().out
    assert "[due 2000-01-01] OVERDUE" in out


def test_list_does_not_mark_done_task_overdue(capsys):
    main(["add", "pay rent", "--due", "2000-01-01"])
    main(["done", "1"])
    capsys.readouterr()
    main(["list", "--all"])
    out = capsys.readouterr().out
    assert "OVERDUE" not in out


def test_add_invalid_due_date_errors():
    with pytest.raises(SystemExit):
        main(["add", "bad date", "--due", "not-a-date"])


def test_add_with_tags_shown_in_list(capsys):
    main(["add", "clean garage", "--tag", "home", "--tag", "chores"])
    main(["list"])
    out = capsys.readouterr().out
    assert "[tags: home, chores]" in out


def test_add_without_tags_shows_no_tags_bracket(capsys):
    main(["add", "no tags here"])
    main(["list"])
    out = capsys.readouterr().out
    assert "[tags:" not in out


def test_add_dedupes_repeated_tags(capsys):
    main(["add", "dedupe me", "--tag", "work", "--tag", "work"])
    main(["list"])
    out = capsys.readouterr().out
    assert "[tags: work]" in out


def test_list_filters_by_tag(capsys):
    main(["add", "work task", "--tag", "work"])
    main(["add", "home task", "--tag", "home"])
    capsys.readouterr()

    main(["list", "--tag", "work"])
    out = capsys.readouterr().out
    assert "work task" in out
    assert "home task" not in out


def test_show_displays_full_detail(capsys):
    main(["add", "renew passport", "--priority", "high", "--due", "2099-01-01", "--tag", "admin"])
    capsys.readouterr()

    assert main(["show", "1"]) == 0
    out = capsys.readouterr().out
    assert "#1 renew passport" in out
    assert "Status: pending" in out
    assert "Priority: high" in out
    assert "Due: 2099-01-01" in out
    assert "OVERDUE" not in out
    assert "Tags: admin" in out
    assert "Created:" in out


def test_show_marks_overdue_task(capsys):
    main(["add", "pay rent", "--due", "2000-01-01"])
    capsys.readouterr()

    main(["show", "1"])
    out = capsys.readouterr().out
    assert "Due: 2000-01-01 (OVERDUE)" in out


def test_show_task_without_due_or_tags(capsys):
    main(["add", "bare task"])
    capsys.readouterr()

    main(["show", "1"])
    out = capsys.readouterr().out
    assert "Due: (none)" in out
    assert "Tags: (none)" in out
    assert "Repeat: (none)" in out


def test_add_with_repeat_shown_in_list(capsys):
    main(["add", "take out the trash", "--repeat", "weekly"])
    main(["list"])
    out = capsys.readouterr().out
    assert "[repeat: weekly]" in out


def test_add_without_repeat_shows_no_repeat_bracket(capsys):
    main(["add", "one-off task"])
    main(["list"])
    out = capsys.readouterr().out
    assert "[repeat:" not in out


def test_show_displays_repeat(capsys):
    main(["add", "daily standup", "--repeat", "daily"])
    capsys.readouterr()

    main(["show", "1"])
    out = capsys.readouterr().out
    assert "Repeat: daily" in out


def test_add_invalid_repeat_choice_errors():
    with pytest.raises(SystemExit):
        main(["add", "bad repeat", "--repeat", "monthly"])


def test_show_done_task_includes_completed_at(capsys):
    main(["add", "finish report"])
    main(["done", "1"])
    capsys.readouterr()

    main(["show", "1"])
    out = capsys.readouterr().out
    assert "Status: done" in out
    assert "Completed:" in out


def test_show_unknown_id_errors():
    assert main(["show", "999"]) == 1


def test_edit_changes_title(capsys):
    main(["add", "original title"])
    capsys.readouterr()

    assert main(["edit", "1", "corrected title"]) == 0
    capsys.readouterr()

    main(["list"])
    out = capsys.readouterr().out
    assert "corrected title" in out
    assert "original title" not in out


def test_edit_unknown_id_errors():
    assert main(["edit", "999", "new title"]) == 1


def test_rm_removes_task(capsys):
    main(["add", "temp task"])
    assert main(["rm", "1"]) == 0
    capsys.readouterr()
    main(["list", "--all"])
    assert "temp task" not in capsys.readouterr().out


def test_rm_unknown_id_errors():
    assert main(["rm", "999"]) == 1


def test_find_matches_task_titles(capsys):
    main(["add", "write the onboarding docs"])
    main(["add", "fix a parser bug"])
    main(["add", "review the docs one more time"])
    capsys.readouterr()

    main(["find", "docs"])
    out = capsys.readouterr().out
    assert "onboarding docs" in out
    assert "review the docs" in out
    assert "fix a parser bug" not in out


def test_find_is_case_insensitive(capsys):
    main(["add", "Renew the PASSPORT"])
    capsys.readouterr()

    main(["find", "passport"])
    out = capsys.readouterr().out
    assert "Renew the PASSPORT" in out


def test_find_excludes_done_tasks_by_default(capsys):
    main(["add", "finish the docs"])
    main(["done", "1"])
    capsys.readouterr()

    main(["find", "docs"])
    out = capsys.readouterr().out
    assert "No matching tasks." in out


def test_find_all_includes_done_tasks(capsys):
    main(["add", "finish the docs"])
    main(["done", "1"])
    capsys.readouterr()

    main(["find", "docs", "--all"])
    out = capsys.readouterr().out
    assert "finish the docs" in out


def test_find_no_matches(capsys):
    main(["add", "an entry about cooking"])
    capsys.readouterr()

    assert main(["find", "gardening"]) == 0
    out = capsys.readouterr().out
    assert "No matching tasks." in out


def test_find_sorts_by_priority(capsys):
    main(["add", "docs low", "--priority", "low"])
    main(["add", "docs high", "--priority", "high"])
    capsys.readouterr()

    main(["find", "docs"])
    out = capsys.readouterr().out
    assert out.index("docs high") < out.index("docs low")


def test_journal_appends_entry(capsys, tmp_path):
    assert main(["journal", "wrote some code today"]) == 0
    out = capsys.readouterr().out
    assert "Journaled #1" in out

    entries = JournalStore(data_dir=tmp_path).load()
    assert len(entries) == 1
    assert entries[0].body == "wrote some code today"


def test_journal_entries_get_incrementing_ids(tmp_path):
    main(["journal", "first"])
    main(["journal", "second"])

    entries = JournalStore(data_dir=tmp_path).load()
    assert [e.id for e in entries] == [1, 2]
    assert [e.body for e in entries] == ["first", "second"]


def test_journal_does_not_affect_task_list(capsys):
    main(["add", "a task"])
    main(["journal", "an entry"])
    capsys.readouterr()

    main(["list"])
    out = capsys.readouterr().out
    assert "a task" in out


def test_journal_without_text_opens_editor(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(
        "onepact.cli._read_entry_from_editor", lambda: "a longer entry\nwritten in $EDITOR\n"
    )

    assert main(["journal"]) == 0
    out = capsys.readouterr().out
    assert "Journaled #1" in out

    entries = JournalStore(data_dir=tmp_path).load()
    assert entries[0].body == "a longer entry\nwritten in $EDITOR"


def test_journal_empty_editor_entry_aborts(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr("onepact.cli._read_entry_from_editor", lambda: "   \n")

    assert main(["journal"]) == 1
    err = capsys.readouterr().err
    assert "Empty entry" in err
    assert JournalStore(data_dir=tmp_path).load() == []


def test_journal_whitespace_only_text_aborts(tmp_path):
    assert main(["journal", "   "]) == 1
    assert JournalStore(data_dir=tmp_path).load() == []


def test_journal_editor_failure_reported(monkeypatch, capsys):
    def _boom():
        raise OSError("no such editor")

    monkeypatch.setattr("onepact.cli._read_entry_from_editor", _boom)

    assert main(["journal"]) == 1
    err = capsys.readouterr().err
    assert "Could not open editor" in err


def test_journal_list_empty(capsys):
    assert main(["journal", "list"]) == 0
    out = capsys.readouterr().out
    assert "No journal entries." in out


def test_journal_list_shows_most_recent_first(capsys):
    main(["journal", "first entry"])
    main(["journal", "second entry"])
    main(["journal", "third entry"])
    capsys.readouterr()

    main(["journal", "list"])
    out = capsys.readouterr().out
    assert out.index("third entry") < out.index("second entry") < out.index("first entry")


def test_journal_list_respects_limit(capsys):
    main(["journal", "first entry"])
    main(["journal", "second entry"])
    main(["journal", "third entry"])
    capsys.readouterr()

    main(["journal", "list", "--limit", "2"])
    out = capsys.readouterr().out
    assert "third entry" in out
    assert "second entry" in out
    assert "first entry" not in out


def test_journal_list_shows_only_first_line_of_multiline_entry(capsys, tmp_path):
    main(["journal", "line one"])
    capsys.readouterr()

    store = JournalStore(data_dir=tmp_path)
    entries = store.load()
    entries[0].body = "line one\nline two"
    store.save(entries)

    main(["journal", "list"])
    out = capsys.readouterr().out
    assert "line one" in out
    assert "line two" not in out


def test_journal_list_invalid_limit_errors():
    with pytest.raises(SystemExit):
        main(["journal", "list", "--limit", "0"])
    with pytest.raises(SystemExit):
        main(["journal", "list", "--limit", "not-a-number"])


def test_journal_show_displays_full_entry(capsys):
    main(["journal", "wrote some tests today"])
    capsys.readouterr()

    assert main(["journal", "show", "1"]) == 0
    out = capsys.readouterr().out
    assert "#1 [" in out
    assert "wrote some tests today" in out


def test_journal_show_displays_full_multiline_body(capsys, tmp_path):
    main(["journal", "line one"])
    capsys.readouterr()

    store = JournalStore(data_dir=tmp_path)
    entries = store.load()
    entries[0].body = "line one\nline two"
    store.save(entries)

    main(["journal", "show", "1"])
    out = capsys.readouterr().out
    assert "line one" in out
    assert "line two" in out


def test_journal_show_unknown_id_errors():
    assert main(["journal", "show", "999"]) == 1


def test_journal_add_with_task_links_entry(capsys, tmp_path):
    main(["add", "write the report"])
    capsys.readouterr()

    assert main(["journal", "finished a draft", "--task", "1"]) == 0
    out = capsys.readouterr().out
    assert "linked to task #1" in out

    entries = JournalStore(data_dir=tmp_path).load()
    assert entries[0].task_id == 1


def test_journal_add_with_unknown_task_errors(capsys, tmp_path):
    assert main(["journal", "orphaned note", "--task", "999"]) == 1
    err = capsys.readouterr().err
    assert "No task with id 999" in err
    assert JournalStore(data_dir=tmp_path).load() == []


def test_journal_list_shows_linked_task(capsys):
    main(["add", "write the report"])
    main(["journal", "finished a draft", "--task", "1"])
    capsys.readouterr()

    main(["journal", "list"])
    out = capsys.readouterr().out
    assert "[task #1]" in out


def test_journal_show_displays_linked_task(capsys):
    main(["add", "write the report"])
    main(["journal", "finished a draft", "--task", "1"])
    capsys.readouterr()

    main(["journal", "show", "1"])
    out = capsys.readouterr().out
    assert "Task: #1" in out


def test_journal_show_displays_no_task_when_unlinked(capsys):
    main(["journal", "a standalone note"])
    capsys.readouterr()

    main(["journal", "show", "1"])
    out = capsys.readouterr().out
    assert "Task: (none)" in out


def test_journal_search_finds_matching_entries(capsys):
    main(["journal", "wrote the onboarding docs"])
    main(["journal", "fixed a bug in the parser"])
    main(["journal", "reviewed the docs one more time"])
    capsys.readouterr()

    main(["journal", "search", "docs"])
    out = capsys.readouterr().out
    assert "onboarding docs" in out
    assert "reviewed the docs" in out
    assert "fixed a bug" not in out


def test_journal_search_is_case_insensitive(capsys):
    main(["journal", "Wrote the ONBOARDING docs"])
    capsys.readouterr()

    main(["journal", "search", "onboarding"])
    out = capsys.readouterr().out
    assert "Wrote the ONBOARDING docs" in out


def test_journal_search_shows_most_recent_match_first(capsys):
    main(["journal", "docs pass one"])
    main(["journal", "unrelated entry"])
    main(["journal", "docs pass two"])
    capsys.readouterr()

    main(["journal", "search", "docs"])
    out = capsys.readouterr().out
    assert out.index("docs pass two") < out.index("docs pass one")


def test_journal_search_no_matches(capsys):
    main(["journal", "an entry about cooking"])
    capsys.readouterr()

    assert main(["journal", "search", "gardening"]) == 0
    out = capsys.readouterr().out
    assert "No matching journal entries." in out


def test_journal_search_on_empty_store(capsys):
    assert main(["journal", "search", "anything"]) == 0
    out = capsys.readouterr().out
    assert "No matching journal entries." in out


def test_journal_add_explicit_keyword_still_works(capsys, tmp_path):
    assert main(["journal", "add", "explicit add keyword"]) == 0
    out = capsys.readouterr().out
    assert "Journaled #1" in out
    assert JournalStore(data_dir=tmp_path).load()[0].body == "explicit add keyword"


def test_journal_editor_entry_can_link_to_task(monkeypatch, capsys, tmp_path):
    main(["add", "write the report"])
    capsys.readouterr()
    monkeypatch.setattr("onepact.cli._read_entry_from_editor", lambda: "drafted it\n")

    assert main(["journal", "--task", "1"]) == 0
    out = capsys.readouterr().out
    assert "linked to task #1" in out

    entries = JournalStore(data_dir=tmp_path).load()
    assert entries[0].body == "drafted it"
    assert entries[0].task_id == 1


def test_read_entry_from_editor_prefers_EDITOR_over_VISUAL(tmp_path, monkeypatch):
    editor_script = tmp_path / "editor.sh"
    editor_script.write_text('#!/bin/sh\necho "from EDITOR" > "$1"\n')
    editor_script.chmod(0o755)
    visual_script = tmp_path / "visual.sh"
    visual_script.write_text('#!/bin/sh\necho "from VISUAL" > "$1"\n')
    visual_script.chmod(0o755)

    monkeypatch.setenv("EDITOR", str(editor_script))
    monkeypatch.setenv("VISUAL", str(visual_script))

    assert _read_entry_from_editor() == "from EDITOR\n"


def test_read_entry_from_editor_falls_back_to_VISUAL(tmp_path, monkeypatch):
    visual_script = tmp_path / "visual.sh"
    visual_script.write_text('#!/bin/sh\necho "from VISUAL" > "$1"\n')
    visual_script.chmod(0o755)

    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.setenv("VISUAL", str(visual_script))

    assert _read_entry_from_editor() == "from VISUAL\n"


def test_read_entry_from_editor_cleans_up_tempfile(tmp_path, monkeypatch):
    script = tmp_path / "fake_editor.sh"
    marker = tmp_path / "editor_target.txt"
    script.write_text(f'#!/bin/sh\necho "$1" > {marker}\necho "hello" > "$1"\n')
    script.chmod(0o755)

    monkeypatch.setenv("EDITOR", str(script))
    monkeypatch.delenv("VISUAL", raising=False)

    _read_entry_from_editor()

    target_path = marker.read_text().strip()
    assert not os.path.exists(target_path)


def test_journal_rm_with_yes_flag_skips_prompt(capsys, tmp_path):
    main(["journal", "entry to remove"])
    capsys.readouterr()

    assert main(["journal", "rm", "1", "--yes"]) == 0
    out = capsys.readouterr().out
    assert "Removed #1" in out
    assert JournalStore(data_dir=tmp_path).load() == []


def test_journal_rm_short_yes_flag(tmp_path):
    main(["journal", "entry to remove"])

    assert main(["journal", "rm", "1", "-y"]) == 0
    assert JournalStore(data_dir=tmp_path).load() == []


def test_journal_rm_confirmed_removes_entry(monkeypatch, capsys, tmp_path):
    main(["journal", "entry to remove"])
    capsys.readouterr()
    monkeypatch.setattr("builtins.input", lambda prompt="": "y")

    assert main(["journal", "rm", "1"]) == 0
    out = capsys.readouterr().out
    assert "Removed #1" in out
    assert JournalStore(data_dir=tmp_path).load() == []


def test_journal_rm_declined_keeps_entry(monkeypatch, capsys, tmp_path):
    main(["journal", "entry to keep"])
    capsys.readouterr()
    monkeypatch.setattr("builtins.input", lambda prompt="": "n")

    assert main(["journal", "rm", "1"]) == 1
    out = capsys.readouterr().out
    assert "Aborted." in out
    entries = JournalStore(data_dir=tmp_path).load()
    assert len(entries) == 1
    assert entries[0].body == "entry to keep"


def test_journal_rm_prompt_includes_id_and_preview(monkeypatch, capsys):
    main(["journal", "buy milk and eggs"])
    capsys.readouterr()
    captured_prompt = {}

    def fake_input(prompt=""):
        captured_prompt["value"] = prompt
        return "n"

    monkeypatch.setattr("builtins.input", fake_input)
    main(["journal", "rm", "1"])

    assert "#1" in captured_prompt["value"]
    assert "buy milk and eggs" in captured_prompt["value"]


def test_journal_rm_unknown_id_errors(capsys):
    assert main(["journal", "rm", "999"]) == 1
    err = capsys.readouterr().err
    assert "No journal entry with id 999" in err


def test_journal_rm_eof_on_prompt_aborts(monkeypatch, tmp_path):
    main(["journal", "entry to keep"])

    def raise_eof(prompt=""):
        raise EOFError

    monkeypatch.setattr("builtins.input", raise_eof)

    assert main(["journal", "rm", "1"]) == 1
    entries = JournalStore(data_dir=tmp_path).load()
    assert len(entries) == 1


def test_list_output_has_no_ansi_codes_by_default(capsys):
    main(["add", "plain task", "--due", "2000-01-01", "--tag", "work"])
    capsys.readouterr()

    main(["list"])
    out = capsys.readouterr().out
    assert "\033[" not in out


def test_list_output_is_colorized_when_forced_on(monkeypatch, capsys):
    monkeypatch.setattr("onepact.cli.should_color", lambda: True)
    main(["add", "colorful task", "--priority", "high", "--due", "2000-01-01", "--tag", "work"])
    capsys.readouterr()

    main(["list"])
    out = capsys.readouterr().out
    assert "\033[31m(high)\033[0m" in out
    assert "\033[31;1m OVERDUE\033[0m" in out
    assert "\033[36m [tags: work]\033[0m" in out


def test_find_output_is_colorized_when_forced_on(monkeypatch, capsys):
    monkeypatch.setattr("onepact.cli.should_color", lambda: True)
    main(["add", "colorful task", "--priority", "low"])
    capsys.readouterr()

    main(["find", "colorful"])
    out = capsys.readouterr().out
    assert "\033[34m(low)\033[0m" in out


def test_show_output_is_colorized_when_forced_on(monkeypatch, capsys):
    monkeypatch.setattr("onepact.cli.should_color", lambda: True)
    main(["add", "colorful task", "--priority", "med", "--due", "2000-01-01"])
    capsys.readouterr()

    main(["show", "1"])
    out = capsys.readouterr().out
    assert "Status: \033[33mpending\033[0m" in out
    assert "Priority: \033[33mmed\033[0m" in out
    assert "\033[31;1m (OVERDUE)\033[0m" in out


def test_journal_list_output_is_colorized_when_forced_on(monkeypatch, capsys):
    monkeypatch.setattr("onepact.cli.should_color", lambda: True)
    main(["add", "linked task"])
    main(["journal", "an entry", "--task", "1"])
    capsys.readouterr()

    main(["journal", "list"])
    out = capsys.readouterr().out
    assert "\033[36m [task #1]\033[0m" in out
