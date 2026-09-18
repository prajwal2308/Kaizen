import io

from onepact.color import colorize, should_color


class _FakeStream(io.StringIO):
    def __init__(self, is_a_tty: bool):
        super().__init__()
        self._is_a_tty = is_a_tty

    def isatty(self) -> bool:
        return self._is_a_tty


def test_should_color_true_for_tty_without_no_color(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert should_color(_FakeStream(True)) is True


def test_should_color_false_for_non_tty(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert should_color(_FakeStream(False)) is False


def test_should_color_false_when_no_color_set(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    assert should_color(_FakeStream(True)) is False


def test_should_color_false_when_no_color_set_to_empty_string(monkeypatch):
    # Per no-color.org, presence of the var disables color regardless of value.
    monkeypatch.setenv("NO_COLOR", "")
    assert should_color(_FakeStream(True)) is False


def test_should_color_handles_stream_without_isatty(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert should_color(object()) is False


def test_colorize_wraps_text_when_enabled():
    result = colorize("hi", "red", enabled=True)
    assert result == "\033[31mhi\033[0m"


def test_colorize_combines_multiple_styles():
    result = colorize("hi", "red", "bold", enabled=True)
    assert result == "\033[31;1mhi\033[0m"


def test_colorize_returns_plain_text_when_disabled():
    assert colorize("hi", "red", enabled=False) == "hi"


def test_colorize_empty_text_stays_empty():
    assert colorize("", "red", enabled=True) == ""
