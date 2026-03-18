from __future__ import annotations

from types import SimpleNamespace

from PIL import Image

from brailliant.canvas import Canvas, DrawMode, _draw_rectangle
from brailliant.cli import display_sparkline
from brailliant.cli_utils import setup_terminal
from brailliant.sparklines import sparkline, sparkline_non_normalized


def test_setup_terminal_skips_non_tty(monkeypatch) -> None:
    fake_stdout = SimpleNamespace(isatty=lambda: False)

    def fail_terminal_size():
        raise AssertionError("get_terminal_size should not be called for non-tty output")

    monkeypatch.setattr("brailliant.cli_utils.sys.stdout", fake_stdout)
    monkeypatch.setattr("brailliant.cli_utils.get_terminal_size", fail_terminal_size)

    setup_terminal(5)


def test_draw_image_has_no_filesystem_side_effect(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    canvas = Canvas(2, 4)
    image = Image.new("1", (2, 4), 1)

    canvas.draw_image(image)

    assert not (tmp_path / "final_img.png").exists()


def test_draw_arrow_renders_without_raising() -> None:
    canvas = Canvas(20, 20)
    blank = canvas.copy()

    canvas.draw_arrow((1, 1), (12, 12))

    assert canvas != blank


def test_draw_rectangle_rotates_around_anchor() -> None:
    points = set(_draw_rectangle(10, 20, 4, 6, rotation=90, anchor_x=0.5, anchor_y=0.5))

    assert {(15, 21), (15, 25), (9, 25), (9, 21)}.issubset(points)


def test_sparkline_constant_series_width() -> None:
    assert sparkline([1, 1, 1, 1], min_val=None, max_val=None) == "⠀⠀"


def test_sparkline_empty_iterables_keep_requested_width() -> None:
    assert sparkline((value for value in ()), width=3) == "⠀⠀⠀"
    assert sparkline_non_normalized((value for value in ()), width=2) == "⠀⠀"


def test_display_sparkline_forwards_log_scale(monkeypatch) -> None:
    seen = {}
    fake_args = SimpleNamespace(
        width=80,
        max=None,
        min=None,
        color=False,
        filled=True,
        log_scale=True,
        title=None,
    )

    class FakeStdout:
        def write(self, _text: str) -> None:
            pass

        def flush(self) -> None:
            pass

    def fake_sparkline(values, width, filled, min_val, max_val, log_scale=False, **_kwargs):
        seen["values"] = list(values)
        seen["log_scale"] = log_scale
        return "ok"

    monkeypatch.setattr("argparse.ArgumentParser.parse_args", lambda self: fake_args)
    monkeypatch.setattr("brailliant.cli.sparkline", fake_sparkline)
    monkeypatch.setattr("brailliant.cli.sys.stdin", SimpleNamespace(buffer=[b"1 2 3\n"]))
    monkeypatch.setattr("brailliant.cli.sys.stdout", FakeStdout())

    display_sparkline()

    assert seen == {"values": [1, 2, 3], "log_scale": True}


def test_draw_border_clear_mode_clears_border() -> None:
    canvas = Canvas(12, 12)
    canvas.fill()

    canvas.draw_border(margin=2, mode=DrawMode.CLEAR)

    assert canvas != Canvas(12, 12).fill()
    border_index = (canvas.height - 2 - 1) * canvas.width + 2
    interior_index = (canvas.height - 5 - 1) * canvas.width + 5
    assert canvas._canvas[border_index] == 0
    assert canvas._canvas[interior_index] == 1


def test_display_sparkline_colorizes_terminal_output(monkeypatch) -> None:
    fake_args = SimpleNamespace(
        width=80,
        max=None,
        min=None,
        color=True,
        filled=True,
        log_scale=False,
        title=None,
    )
    writes = []

    class FakeStdout:
        def isatty(self) -> bool:
            return True

        def write(self, text: str) -> None:
            writes.append(text)

        def flush(self) -> None:
            pass

    monkeypatch.setattr("argparse.ArgumentParser.parse_args", lambda self: fake_args)
    monkeypatch.setattr("brailliant.cli.sys.stdin", SimpleNamespace(buffer=[b"1 2 3\n"]))
    monkeypatch.setattr("brailliant.cli.sys.stdout", FakeStdout())

    display_sparkline()

    assert any("\033[36m" in text for text in writes)
