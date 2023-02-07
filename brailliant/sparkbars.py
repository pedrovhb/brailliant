import itertools
import math
from typing import Literal, Iterable

from brailliant import (
    coords_braille_mapping,
    BRAILLE_RANGE_START,
    braille_table_str,
    BRAILLE_COLS,
    BRAILLE_ROWS,
    coords_to_braille,
)


def get_sparkbar(
    data: Iterable[float],
    min_width: int | None = None,
    max_width: int | None = 80,
    min_val: float | None = 0,
    max_val: float | None = None,
) -> str:
    """Return a sparkline-like string with up to 4 horizontal bars.

    Args:
        data: The data to be represented as a sparkline.
        min_width: The width of the sparkline.
        max_width: The maximum width of the sparkline.
        min_val: The bottom of the sparkline, or `None` to use the minimum value in the data.
        max_val: The top of the sparkline, or `None` to use the maximum value in the data.

    Returns:
        The sparkline as a string.

    Examples:

        >>> get_sparkbar(3, 4, 1)
        '⣦⡤'

        >>> get_sparkbar(3, 4, 1, min_width=10)
        '⣦⡤⠀⠀⠀⠀⠀⠀⠀⠀'

        >>> get_sparkbar(3, 4, 1, min_width=10, max_width=20)
        '⣦⡤⠀⠀⠀⠀⠀⠀⠀⠀'
    """

    if len(data) > 4:
        raise ValueError("Data must have at most 4 elements.")

    if not data:
        return "⠀" * min_width if min_width is not None else ""

    if min_val is None and data:
        _min_val = min(data)
    else:
        _min_val = min_val or 0

    if max_val is None and data:
        _max_val = max(data)
    else:
        _max_val = max_val or 0

    scale = _max_val - _min_val
    if scale == 0:
        scale = 1

    # Get the length in dots for each horizontal bar. Since there's 4 vertical
    # dots per character, we'll have 4 rows.
    rows_lengths = [0, 0, 0, 0]
    for i, value in enumerate(data):
        val = math.ceil(value - _min_val)
        if min_width is not None:
            val = max(0, min(min_width, val))
        rows_lengths[i] = val * 2

    # Use the mapping to convert the columns of braille dots into braille characters.

    # unbound_num_chars is the number of characters we'd use if there were no
    # min_width or max_width restrictions, i.e. the number of dots divided by 2
    # (since there are 2 horizontal dots per character).
    unbound_num_chars = math.ceil(scale / 2)
    if min_width is None and max_width is None:
        num_chars = unbound_num_chars
    else:
        # Clamp unbound_num_chars to the min_width and max_width.
        num_chars = unbound_num_chars
        if max_width is not None:
            num_chars = min(num_chars, max_width)
        if min_width is not None:
            num_chars = max(num_chars, min_width)

    chars = []
    for i in range(num_chars):
        char = 0
        for j, length in enumerate(rows_lengths):
            if length > i:
                char |= coords_braille_mapping[0, j]
            if length > i + 1:
                char |= coords_braille_mapping[1, j]
        chars.append(char)

    return "".join(braille_table_str[c] for c in chars)  # todo - fix this function


def get_sparkbar_normalized(
    data: Iterable[float],
    width: int = 40,
    min_data_value: float | None = None,
    max_data_value: float | None = None,
) -> str:
    """Return a normalized sparkbar.

    If max_width is specified and its value is exceeded by the values, values will be normalized
    to fit within that many characters.

    If min_width is specified and the data contains only values which don't reach that, the
    values will be normalized to stretch the data, so it fills the width.

    If max_width is not specified, the sparkbar will be as wide as the data requires (i.e. a
    data set with a max value of 10 and a min value of 0 will be 5 characters wide, as one
    character can fit 2 dots horizontally).

    Args:
        min_width: The minimum width of the sparkbar.
        max_width: The maximum width of the sparkbar.

    Returns:
        A sparkbar string.


    """
    min_val = min(data)
    max_val = max(data)

    if min_data_value is not None:
        min_val = min(min_val, min_data_value)
    if max_data_value is not None:
        max_val = max(max_val, max_data_value)

    data = tuple(data)
    if min_val < 0:
        data = tuple(value - min_val for value in data)
        min_val = 0
    val_range = max_val - min_val or 1
    val_scale = 2 * width / val_range
    char_normalized_data = tuple(val * val_scale for val in data)

    return get_sparkbar(char_normalized_data)


if __name__ == "__main__":
    bar_data_large_range: list[float] = [-10, 40, 60, 0]
    bar_data_medium_range: list[float] = [1, 1, 5, 6]
    bar_data_small_range: list[float] = [0, 0, 0, 1]

    for fn, data in itertools.product(
        (get_sparkbar, get_sparkbar_normalized),
        (bar_data_small_range, bar_data_medium_range, bar_data_large_range),
    ):
        print(f"{fn.__name__} - {data}\n")
        print(fn(data))
        print("\n")
