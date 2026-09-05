import pytest

from onepact.cli import main
from onepact.storage import JournalStore, TaskStore


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr("onepact.cli.TaskStore", lambda: TaskStore(data_dir=tmp_path))
    monkeypatch.setattr("onepact.cli.JournalStore", lambda: JournalStore(data_dir=tmp_path))


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
