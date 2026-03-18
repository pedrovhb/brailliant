from __future__ import annotations

import pytest

from brailliant._experimental.sparkbars import get_sparkbar, get_sparkbar_normalized


def test_get_sparkbar_examples() -> None:
    assert get_sparkbar([3, 4, 1]) == "⣦⡤"
    assert get_sparkbar([3, 4, 1], min_width=10) == "⣦⡤" + "⠀" * 8


def test_get_sparkbar_limits_and_padding() -> None:
    assert get_sparkbar([8, 8], max_width=2) == "⣤⣤"
    assert get_sparkbar([], min_width=3) == "⠀⠀⠀"
    assert get_sparkbar([-3, -1], min_val=0, min_width=2) == "⠀⠀"


def test_get_sparkbar_validation() -> None:
    with pytest.raises(ValueError):
        get_sparkbar([1, 2, 3, 4, 5])

    with pytest.raises(ValueError):
        get_sparkbar([1], min_width=4, max_width=2)


def test_get_sparkbar_normalized_width() -> None:
    result = get_sparkbar_normalized([10, 30, 20], width=6)

    assert len(result) == 6
    assert result.endswith("⠤")


def test_get_sparkbar_normalized_respects_explicit_bounds() -> None:
    assert get_sparkbar_normalized([5, 15, 25], width=4, min_data_value=10, max_data_value=20) == "⠶⠶⠒⠒"


def test_get_sparkbar_normalized_validation() -> None:
    with pytest.raises(ValueError):
        get_sparkbar_normalized([1, 2], width=4, min_data_value=5, max_data_value=3)

    with pytest.raises(ValueError):
        get_sparkbar_normalized([], width=4, min_data_value=5, max_data_value=3)


def test_get_sparkbar_normalized_empty() -> None:
    assert get_sparkbar_normalized([], width=4) == "⠀⠀⠀⠀"
