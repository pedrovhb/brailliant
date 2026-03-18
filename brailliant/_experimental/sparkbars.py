from __future__ import annotations

import math
from typing import Iterable

from brailliant import braille_table_str, coords_braille_mapping


def _coerce_data(data: Iterable[float]) -> tuple[float, ...]:
    if not isinstance(data, (list, tuple)):
        data = tuple(data)
    else:
        data = tuple(data)

    if len(data) > 4:
        raise ValueError("Data must have at most 4 elements.")

    return data


def get_sparkbar(
    data: Iterable[float],
    min_width: int | None = None,
    max_width: int | None = 80,
    min_val: float | None = 0,
    max_val: float | None = None,
) -> str:
    """Return a sparkline-like string with up to 4 horizontal bars.

    Each input value is treated as a horizontal length measured in braille-dot columns.
    Up to four values can be displayed, one per braille row from top to bottom.

    Args:
        data: The row lengths to represent.
        min_width: Minimum output width in braille characters.
        max_width: Maximum output width in braille characters.
        min_val: Minimum input value to consider. Values below this are clipped.
        max_val: Maximum input value to consider. Values above this are clipped.

    Returns:
        The sparkbar as a string.

    Examples:
        >>> get_sparkbar([3, 4, 1])
        '⣦⡤'

        >>> get_sparkbar([3, 4, 1], min_width=10)
        '⣦⡤⠀⠀⠀⠀⠀⠀'

        >>> get_sparkbar([3, 4, 1], min_width=10, max_width=20)
        '⣦⡤⠀⠀⠀⠀⠀⠀'
    """
    data = _coerce_data(data)

    if min_width is not None and min_width < 0:
        raise ValueError("min_width must be at least 0")
    if max_width is not None and max_width < 0:
        raise ValueError("max_width must be at least 0")
    if min_width is not None and max_width is not None and min_width > max_width:
        raise ValueError("min_width cannot be greater than max_width")

    if not data:
        return "⠀" * min_width if min_width is not None else ""

    _min_val = min(data) if min_val is None else min_val
    _max_val = max(max(data), _min_val) if max_val is None else max_val
    if max_val is not None and _max_val < _min_val:
        raise ValueError("max_val must be greater than or equal to min_val")

    row_lengths = tuple(max(0, math.ceil(min(value, _max_val) - _min_val)) for value in data)
    num_chars = math.ceil(max(row_lengths, default=0) / 2)

    if max_width is not None:
        num_chars = min(num_chars, max_width)
    if min_width is not None:
        num_chars = max(num_chars, min_width)

    max_dots = num_chars * 2
    row_lengths = tuple(min(length, max_dots) for length in row_lengths)

    chars = []
    for char_index in range(num_chars):
        char = 0
        left_dot = char_index * 2
        right_dot = left_dot + 1
        for row_index, row_length in enumerate(row_lengths):
            if row_length > left_dot:
                char |= coords_braille_mapping[(0, row_index)]
            if row_length > right_dot:
                char |= coords_braille_mapping[(1, row_index)]
        chars.append(braille_table_str[char])

    return "".join(chars)


def get_sparkbar_normalized(
    data: Iterable[float],
    width: int = 40,
    min_data_value: float | None = None,
    max_data_value: float | None = None,
) -> str:
    """Return a normalized sparkbar.

    Input values are scaled to fit exactly within the requested character width.

    Args:
        data: The values to render.
        width: Output width in braille characters.
        min_data_value: Explicit lower bound for normalization.
        max_data_value: Explicit upper bound for normalization.

    Returns:
        A normalized sparkbar string.
    """
    if width < 0:
        raise ValueError("width must be at least 0")
    if min_data_value is not None and max_data_value is not None and max_data_value < min_data_value:
        raise ValueError("max_data_value must be greater than or equal to min_data_value")

    data = _coerce_data(data)
    if not data:
        return "⠀" * width

    min_val = min_data_value if min_data_value is not None else min(data)
    max_val = max_data_value if max_data_value is not None else max(data)

    dot_width = width * 2
    val_range = max_val - min_val
    if val_range == 0:
        scaled_data = [0] * len(data)
    else:
        scaled_data = [
            max(0, math.ceil((min(value, max_val) - min_val) / val_range * dot_width))
            for value in data
        ]

    return get_sparkbar(scaled_data, min_width=width, max_width=width, min_val=0, max_val=dot_width)


__all__ = ("get_sparkbar", "get_sparkbar_normalized")
