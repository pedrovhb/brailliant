from __future__ import annotations

import itertools
import math
from typing import Iterable, Literal

from brailliant import (
    braille_table_str,
    coords_braille_mapping,
    coords_braille_mapping_filled,
)

INV_LOG1P_1 = 1 / math.log1p(1)


def sparkline_non_normalized(
    data: Iterable[int],
    width: int | None = None,
    filled: bool = True,
) -> str:
    """Return a sparkline of the numerical data without normalizing the data.

    Data must be in the range [0, 4], with 0 being no dot at the corresponding x-coordinate
    and 4 being all dots.

    Args:
        data: The data to be represented as a sparkline.
        width: The width of the sparkline. If None, the width will be the length of the data.
        filled: Whether the sparkline should be filled.

    Returns:
        The sparkline as a string.

    Examples:
        >>> sparkline_non_normalized([1, 2, 3, 3, 4, 2, 3, 3, 3, 2])
        '⣠⣶⣧⣶⣦'

        >>> sparkline_non_normalized([1, 2, 3, 4, 0, 2, 3, 4, 3, 2, 1], filled=True, width=20)
        '⣠⣾⢠⣾⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀'
    """

    if not data:
        return "⠀" * width if width is not None else ""

    if not isinstance(data, (list, tuple)):
        data = tuple(min(d, 4) for d in data)

    if width is not None:
        if width < 1:
            raise ValueError("width must be at least 1")

        # Use only latest values to fill the width
        if len(data) // 2 > width:
            data = data[-width * 2 :]

    mapping = coords_braille_mapping_filled if filled else coords_braille_mapping

    # Here, we'll use the mapping to convert the columns of braille dots into
    # braille characters. We zip them with a 1-element offset so that we can
    # get the one character that represents the two columns.
    evens = [mapping.setdefault((0, left - 1), 0) for left in data[::2]]
    odds = [mapping.setdefault((1, right - 1), 0) for right in data[1::2]]
    chars = [
        braille_table_str[left | right]
        for left, right in itertools.zip_longest(evens, odds, fillvalue=0)
    ]

    if width is not None and len(chars) < width:
        chars.extend(braille_table_str[0] * (width - len(chars)))

    return "".join(chars)


def sparkline(
    data: Iterable[float],
    width: int | None = None,
    filled: bool = True,
    min_val: float | None = 0,
    max_val: float | None = None,
    log_scale: bool = False,
    base_level: Literal[0, 1] = 0,
    rounding: Literal["round", "ceil", "floor"] = "ceil",
) -> str:
    """Return a sparkline of the numerical data. The data will be normalized to the range [0, 4].

    Args:
        data: The data to be represented as a sparkline.

        width: The width of the sparkline. If None, the width will be the length of the data.

        filled: Whether the sparkline should be filled.

        min_val: The bottom of the sparkline, or `None` to use the minimum value in the data. If
            your data has negative values you'd like to take into account in the scale, you should
            set this to `None` to use the minimum value in the data, or to the minimum value you
            want to take into account.

        max_val: The top of the sparkline, or `None` to use the maximum value in the data.

        log_scale: Whether to use a logarithmic scale, which is useful for data with a large
            range.

        base_level: The level at which the sparkline should be filled. If 0, the sparkline will
            contain only the empty braille character for the lowest value (i.e. no dots). If 1,
            the sparkline will always contain at least one dot.

        rounding: The rounding method to use when converting the data to braille dots.

    Returns:
        The sparkline as a string.

    Examples:
        >>> sparkline([0, 2.5, 2.5, 10, 5, 5])
        '⢀⣸⣤'

        >>> sparkline([0, 2.5, 2.5, 10, 5, 5], filled=False, base_level=1)
        '⡠⠌⠒'

        >>> sparkline(
        ...     [0, 0, 0, 0.01, 1, 2, 150, 45, 300, 600, 450, 300, 150, 145, 5],
        ...     log_scale=True,
        ...     width=10,
        ... )
        '⠀⢀⣀⣄⣾⣷⣤⡀⠀⠀'

    Notes:
        I picked defaults of `base_level=0` and `rounding="ceil"` because this combination
            has the neat property that the sparkline will contain no dots only for a value
            of 0 (or the min_val exactly); anything else will have at least one dot. This
            is useful because usually the distinction between 0 non-0 is an important one.

    """
    if not data:
        return "⠀" * width if width is not None else ""

    if not isinstance(data, (list, tuple)):
        data = tuple(data)

    _min_val = min(data) if min_val is None else min_val
    _max_val = max(data) if max_val is None else max_val

    if rounding == "round":
        round_func = round
    elif rounding == "ceil":
        round_func = math.ceil
    elif rounding == "floor":
        round_func = math.floor
    else:
        raise ValueError(f"Invalid rounding method: {rounding}")

    data_range = _max_val - _min_val
    if data_range == 0:
        return "⠀" * min(width, len(data)) if width is not None else "⠀" * len(data)

    data = ((d - _min_val) / data_range for d in data)  # Normalize to [0, 1]

    if log_scale:
        data = (math.log1p(d) * INV_LOG1P_1 for d in data)

    if base_level == 0:
        data = (d * 4 for d in data)
    elif base_level == 1:
        data = (d * 3 + 1 for d in data)
    else:
        raise ValueError(f"Invalid base_level: {base_level}")

    data = (round_func(d) for d in data)
    return sparkline_non_normalized(data, width=width, filled=filled)


__all__ = ("sparkline", "sparkline_non_normalized")
