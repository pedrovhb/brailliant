from __future__ import annotations

import textwrap

import pytest

from brailliant import sparkline, coords_to_braille
from brailliant.canvas import Canvas
from brailliant.sparkbars import get_sparkbar


def test_coords_to_braille():
    assert coords_to_braille((0, 0)) == "⡀"
    assert coords_to_braille((0, 0), (1, 0)) == "⣀"
    assert coords_to_braille((0, 0), (1, 0), (0, 1)) == "⣄"
    assert coords_to_braille((0, 3), (1, 3)) == "⠉"
    assert coords_to_braille((0, 3), (1, 3), (0, 2), (1, 2)) == "⠛"


def test_coords_to_braille_exceptions():
    with pytest.raises(KeyError):
        coords_to_braille((0, -2))
    with pytest.raises(KeyError):
        coords_to_braille((1, -2))
    with pytest.raises(KeyError):
        coords_to_braille((0, 4))
    with pytest.raises(KeyError):
        coords_to_braille((2, 3))
    with pytest.raises(KeyError):
        coords_to_braille((-2, 0))
    with pytest.raises(KeyError):
        coords_to_braille((1, 0), (0, -2))
    with pytest.raises(KeyError):
        coords_to_braille((1, 0), (1, 4))
    with pytest.raises(KeyError):
        coords_to_braille((1, 0), (2, 3))
    with pytest.raises(KeyError):
        coords_to_braille((1, 0), (-1, 0))
    with pytest.raises(KeyError):
        coords_to_braille((1, 0), (0, -2), (1, 4))
    with pytest.raises(KeyError):
        coords_to_braille((1, 0), (0, -2), (2, 3))
    with pytest.raises(KeyError):
        coords_to_braille((1, 0), (0, -2), (-1, 0))


def test_sparklines():
    # Test sparklines
    assert sparkline([1]) == "⡇"

    assert sparkline([1, 1, 5, 5]) == "⣀⣿"
    assert sparkline([1, 1, 1, 5, 5]) == "⣀⣸⡇"

    # Test sparkline with input data of length greater than 1
    assert sparkline([1, 2, 3, 4, 5, 2, 3, 4, 3, 2, 1]) == "⣠⣾⣧⣾⣦⡀"

    # Test sparkline with filled=False
    assert sparkline([1, 2, 3, 4, 5, 2, 3, 4, 3, 2, 1], filled=False) == "⡠⠊⠡⠊⠢⡀"

    # Test sparkline with min_val set to a non-None value
    assert sparkline([1, 2, 3, 4, 5, 2, 3, -4, -3, 2, 1], min_val=2) == "⠀⣴⡇⡄⠀⠀"

    # Test sparkline with min_val set to a non-None negative value
    assert sparkline([1, 2, 3, 4, 5, 2, 3, -4, -3, 2, 1], min_val=-4) == "⣶⣿⣷⡇⣰⡆"

    # Test sparkline with max_val set to a non-None value
    assert sparkline([1, 2, 3, 4, 5, 2, 3, 4, 3, 2, 1], max_val=3) == "⣴⣿⣷⣿⣷⡄"

    # Test sparkline with width set to a non-None value and an odd length
    assert sparkline([1, 1, 1, 5, 5], width=10) == "⣀⣸⡇⠀⠀⠀⠀⠀⠀⠀"

    # Test sparkline with width set to a non-None value and an even length
    assert sparkline([1, 1, 5, 5], width=10) == "⣀⣿⠀⠀⠀⠀⠀⠀⠀⠀"

    # Test sparkline with width set to a non-None value and a larger length
    large_seq = [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5] * 4
    assert sparkline(large_seq, width=10) == "⣿⣿⣇⣀⣤⣴⣶⣿⣿⣿"

    # Test sparkline with all optional parameters set to non-None values
    assert (
        sparkline(
            [1, 2, 3, 4, 5, 2, 3, -4, -3, 2, 1],
            filled=False,
            width=20,
            min_val=0,
            max_val=6,
        )
        == "⡠⠔⠡⠄⠠⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀"
    )


def test_sparkbars_non_normalized():
    assert get_sparkbar((1,), width=10, normalized=False) == "⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀"
    assert get_sparkbar((), width=10, normalized=False) == "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀"
    assert get_sparkbar((1, 4, 5), width=10, normalized=False) == "⡶⠶⠂⠀⠀⠀⠀⠀⠀⠀"
    assert get_sparkbar((3, 4, 1), normalized=False) == "⣦⡤⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀"
    assert get_sparkbar((342, 37, 745), width=20, normalized=False) == "⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣖⣒"
    with pytest.raises(ValueError):
        get_sparkbar((1, 4, 5, 2, 4), normalized=False)


def test_sparkbars_normalized():
    assert get_sparkbar((1,), width=10, normalized=True) == "⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀"
    assert get_sparkbar((), width=10, normalized=True) == "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀"
    assert get_sparkbar((1, 4, 5), width=10, normalized=True) == "⣶⣶⡶⠶⠶⠶⠶⠶⠶⠶"
    # assert get_sparkbar((3, 4, 1), normalized=True) == "⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣦⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤"
    assert get_sparkbar((342, 37, 745), width=20, normalized=True) == "⣶⣖⣒⣒⣒⣒⣒⣒⣒⣒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒"
    with pytest.raises(ValueError):
        get_sparkbar((1, 4, 5, 2, 4), normalized=True)


def test_canvas():
    canvas = Canvas(40, 40)
    canvas_2 = Canvas(40, 40)

    canvas.draw_circle((15, 15), 10)
    canvas_2.draw_circle((25, 25), 10)

    assert (
        canvas.get_str()
        == textwrap.dedent(
            """
            ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
            ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
            ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
            ⠀⠀⠀⠀⠀⣀⡤⠤⠤⣄⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀
            ⠀⠀⠀⣰⠋⠁⠀⠀⠀⠀⠉⢳⡀⠀⠀⠀⠀⠀⠀⠀
            ⠀⠀⢰⠃⠀⠀⠀⠀⠀⠀⠀⠀⢳⠀⠀⠀⠀⠀⠀⠀
            ⠀⠀⢸⡀⠀⠀⠀⠀⠀⠀⠀⠀⣸⠀⠀⠀⠀⠀⠀⠀
            ⠀⠀⠀⢳⡀⠀⠀⠀⠀⠀⠀⣰⠃⠀⠀⠀⠀⠀⠀⠀
            ⠀⠀⠀⠀⠉⠓⠦⠤⠤⠖⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀
            ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
            """
        ).strip()
    )
    assert (
        canvas_2.get_str()
        == textwrap.dedent(
            """
        ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
        ⠀⠀⠀⠀⠀⠀⠀⠀⢀⡤⠖⠋⠉⠉⠓⠦⣄⠀⠀⠀
        ⠀⠀⠀⠀⠀⠀⠀⢀⡞⠀⠀⠀⠀⠀⠀⠀⠘⣆⠀⠀
        ⠀⠀⠀⠀⠀⠀⠀⢸⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠀⠀
        ⠀⠀⠀⠀⠀⠀⠀⠘⣆⠀⠀⠀⠀⠀⠀⠀⢀⡞⠀⠀
        ⠀⠀⠀⠀⠀⠀⠀⠀⠘⠦⣄⡀⠀⠀⣀⡤⠞⠀⠀⠀
        ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠉⠉⠁⠀⠀⠀⠀⠀
        ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
        ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
        ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
        """
        ).strip()
    )

    assert (
        (canvas | canvas_2).get_str()
        == textwrap.dedent(
            """
        ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
        ⠀⠀⠀⠀⠀⠀⠀⠀⢀⡤⠖⠋⠉⠉⠓⠦⣄⠀⠀⠀
        ⠀⠀⠀⠀⠀⠀⠀⢀⡞⠀⠀⠀⠀⠀⠀⠀⠘⣆⠀⠀
        ⠀⠀⠀⠀⠀⣀⡤⢼⠤⣄⡀⠀⠀⠀⠀⠀⠀⢸⠀⠀
        ⠀⠀⠀⣰⠋⠁⠀⠘⣆⠀⠉⢳⡀⠀⠀⠀⢀⡞⠀⠀
        ⠀⠀⢰⠃⠀⠀⠀⠀⠘⠦⣄⡀⢳⠀⣀⡤⠞⠀⠀⠀
        ⠀⠀⢸⡀⠀⠀⠀⠀⠀⠀⠀⠉⣹⠉⠁⠀⠀⠀⠀⠀
        ⠀⠀⠀⢳⡀⠀⠀⠀⠀⠀⠀⣰⠃⠀⠀⠀⠀⠀⠀⠀
        ⠀⠀⠀⠀⠉⠓⠦⠤⠤⠖⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀
        ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
        """
        ).strip()
    )
