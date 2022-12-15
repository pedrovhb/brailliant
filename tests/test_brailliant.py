from __future__ import annotations

import pytest

from brailliant import sparkline, sparkbars, coords_to_braille
from brailliant.canvas import Canvas


def test_coords_to_braille():
    assert coords_to_braille((0, 0)) == "⡀"
    assert coords_to_braille((0, 0), (1, 0)) == "⣀"
    assert coords_to_braille((0, 0), (1, 0), (0, 1)) == "⣄"
    assert coords_to_braille((0, 3), (1, 3)) == "⠉"
    assert coords_to_braille((0, 3), (1, 3), (0, 2), (1, 2)) == "⠛"


def test_coords_to_braille_exceptions():
    with pytest.raises(ValueError):
        coords_to_braille((0, -2))
    with pytest.raises(ValueError):
        coords_to_braille((1, -2))
    with pytest.raises(ValueError):
        coords_to_braille((0, 4))
    with pytest.raises(ValueError):
        coords_to_braille((2, 3))
    with pytest.raises(ValueError):
        coords_to_braille((-2, 0))
    with pytest.raises(ValueError):
        coords_to_braille((1, 0), (0, -2))
    with pytest.raises(ValueError):
        coords_to_braille((1, 0), (1, 4))
    with pytest.raises(ValueError):
        coords_to_braille((1, 0), (2, 3))
    with pytest.raises(ValueError):
        coords_to_braille((1, 0), (-1, 0))
    with pytest.raises(ValueError):
        coords_to_braille((1, 0), (0, -2), (1, 4))
    with pytest.raises(ValueError):
        coords_to_braille((1, 0), (0, -2), (2, 3))
    with pytest.raises(ValueError):
        coords_to_braille((1, 0), (0, -2), (-1, 0))


def test_sparklines():

    # Test sparklines
    assert sparkline([1]) == "⢀"

    assert sparkline([1, 1, 5, 5]) == "⣀⣿"
    assert sparkline([1, 1, 1, 5, 5]) == "⢀⣀⣿"

    # Test sparkline with input data of length greater than 1
    assert sparkline([1, 2, 3, 4, 5, 2, 3, 4, 3, 2, 1]) == "⢀⣴⣾⣴⣶⣄"

    # Test sparkline with filled=False
    assert sparkline([1, 2, 3, 4, 5, 2, 3, 4, 3, 2, 1], filled=False) == "⢀⠔⠊⠔⠒⢄"

    # Test sparkline with min_val set to a non-None value
    assert sparkline([1, 2, 3, 4, 5, 2, 3, -4, -3, 2, 1], min_val=2) == "⢀⣠⣾⣠⣀⣀"

    # Test sparkline with max_val set to a non-None value
    assert sparkline([1, 2, 3, 4, 5, 2, 3, 4, 3, 2, 1], max_val=3) == "⢀⣾⣿⣾⣿⣆"

    # Test sparkline with width set to a non-None value and an odd length
    assert sparkline([1, 1, 1, 5, 5], width=10) == "⠀⠀⠀⠀⠀⠀⠀⢀⣀⣿"

    # Test sparkline with width set to a non-None value and an even length
    assert sparkline([1, 1, 5, 5], width=10) == "⠀⠀⠀⠀⠀⠀⠀⠀⣀⣿"

    # Test sparkline with width set to a non-None value and a larger length
    large_seq = [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5] * 4
    assert sparkline(large_seq, width=10) == "⣶⣿⣇⣀⣤⣴⣶⣶⣾⣿"

    # Test sparkline with all optional parameters set to non-None values
    assert (
        sparkline(
            [1, 2, 3, 4, 5, 2, 3, -4, -3, 2, 1],
            filled=False,
            width=20,
            min_val=0,
            max_val=6,
        )
        == "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠔⠒⠔⣀⢄"
    )


def test_sparkbars():

    assert sparkbars(1, min_width=10) == "⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀"
    assert sparkbars(min_width=10) == "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀"
    assert sparkbars(1, 4, 5, min_width=10) == "⡶⠶⠂⠀⠀⠀⠀⠀⠀⠀"  # todo fix normalization
    with pytest.raises(ValueError):
        sparkbars(1, 4, 5, 2, 4)
    # Test width=None
    assert sparkbars(3, 4, 1) == "⣦⡤"

    assert sparkbars(342, 496, 745, max_width=20) == "⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⠶⠶⠶⠶⠶⠒⠒⠒⠒⠒⠒⠒⠒"
    y = sparkbars(342, 496, 745)


def test_canvas():
    canvas = Canvas(40, 40)
    canvas_2 = Canvas(40, 40)

    canvas.draw_circle((15, 15), 10)
    canvas_2.draw_circle((25, 25), 10)

    assert (
        canvas._canvas
        == 763033752957748975707955474981078844747940135138343112487280712750482088504925844881085130572481548242554666245999255648987315642189244468284813101747374011216693072470685130400669804619571122863613639740844331630936625911066385844427196845889209935569946833307330208148006657935263205449975355278410498122868326400
    )
    assert (
        canvas_2._canvas
        == 1389374714869771738664987720338926102290247147168409398349565467271851599016155316275021181945773259779409874411356187175109517834108114991990355774890252781469845913597372067054255067244541271608898899462613192695743401861067603180562909795070345551365455875329704861524237849010510768530656584934668013032944486201321635411974026288737117544105247451009902264179458405782728815310697953553729402990730060745546433385673523200
    )

    assert (
        (canvas | canvas_2)._canvas
        == 1389374714869771738664987720338926102290247147168409398349565467271851599016155316275021181945773259779409874412119220905596102624037121620355119734775383746383476789305820620625977011032882640802363638446535075637356065467052623845626055729910868917846212522259365206534181354092052043302859679223651991021483856561787420231432676157672136887234639752743192010737871478956434267610963321815846496889925732576204536128324239360
    )
