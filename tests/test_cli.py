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
