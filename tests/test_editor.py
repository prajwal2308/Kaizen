import os

from onepact.editor import read_entry_from_editor


def test_read_entry_from_editor_prepopulates_the_tempfile(tmp_path, monkeypatch):
    script = tmp_path / "fake_editor.sh"
    script.write_text(
        '#!/bin/sh\nexisting=$(cat "$1")\necho "${existing} - appended" > "$1"\n'
    )
    script.chmod(0o755)
    monkeypatch.setenv("EDITOR", str(script))
    monkeypatch.delenv("VISUAL", raising=False)

    assert read_entry_from_editor("original content") == "original content - appended\n"


def test_read_entry_from_editor_prefers_EDITOR_over_VISUAL(tmp_path, monkeypatch):
    editor_script = tmp_path / "editor.sh"
    editor_script.write_text('#!/bin/sh\necho "from EDITOR" > "$1"\n')
    editor_script.chmod(0o755)
    visual_script = tmp_path / "visual.sh"
    visual_script.write_text('#!/bin/sh\necho "from VISUAL" > "$1"\n')
    visual_script.chmod(0o755)

    monkeypatch.setenv("EDITOR", str(editor_script))
    monkeypatch.setenv("VISUAL", str(visual_script))

    assert read_entry_from_editor() == "from EDITOR\n"


def test_read_entry_from_editor_falls_back_to_VISUAL(tmp_path, monkeypatch):
    visual_script = tmp_path / "visual.sh"
    visual_script.write_text('#!/bin/sh\necho "from VISUAL" > "$1"\n')
    visual_script.chmod(0o755)

    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.setenv("VISUAL", str(visual_script))

    assert read_entry_from_editor() == "from VISUAL\n"


def test_read_entry_from_editor_cleans_up_tempfile(tmp_path, monkeypatch):
    script = tmp_path / "fake_editor.sh"
    marker = tmp_path / "editor_target.txt"
    script.write_text(f'#!/bin/sh\necho "$1" > {marker}\necho "hello" > "$1"\n')
    script.chmod(0o755)

    monkeypatch.setenv("EDITOR", str(script))
    monkeypatch.delenv("VISUAL", raising=False)

    read_entry_from_editor()

    target_path = marker.read_text().strip()
    assert not os.path.exists(target_path)
