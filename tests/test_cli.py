import pytest

from kaizen.cli import main
from kaizen.storage import TaskStore


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr("kaizen.cli.TaskStore", lambda: TaskStore(data_dir=tmp_path))


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


def test_add_default_priority_is_med(capsys):
    main(["add", "no priority given"])
    main(["list"])
    out = capsys.readouterr().out
    assert "(med) no priority given" in out


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
