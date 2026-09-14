import os
from datetime import datetime, timedelta, timezone

import pytest

from onepact.cli import _read_entry_from_editor, main
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
