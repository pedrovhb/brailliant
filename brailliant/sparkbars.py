import math
import shutil
from typing import Literal, Iterable

from brailliant import coords_braille_mapping, BRAILLE_RANGE_START


def sparkbars(
    *data: float,
    min_width: int | None = None,
    max_width: int | None = 80,
    min_val: float | None = 0,
    max_val: float | None = None,
    normalize_values: Literal["never", "always", "auto"] = "auto",
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

        >>> sparkbars(3, 4, 1)
        '⣦⡤'

        >>> sparkbars(3, 4, 1, min_width=10)
        '⣦⡤⠀⠀⠀⠀⠀⠀⠀⠀'

        >>> sparkbars(3, 4, 1, min_width=10, max_width=20)
        '⣦⡤⠀⠀⠀⠀⠀⠀⠀⠀'
    """

    if len(data) > 4:
        raise ValueError("Data must have at most 4 elements.")

    if normalize_values == "always" and max_width is None:
        raise ValueError('max_width must be specified if normalize_values is "always".')

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

    if normalize_values == "auto" and max_width is None:
        do_normalize = False
    elif normalize_values == "auto":
        do_normalize = scale > max_width * 2 if max_width is not None else False
    else:
        do_normalize = normalize_values == "always"

    if do_normalize:
        assert max_width is not None
        data = tuple(((v - _min_val) / scale * max_width) for v in data)
        _min_val = 0
        _max_val = max_width

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
        char = BRAILLE_RANGE_START
        for j, length in enumerate(rows_lengths):
            div, mod = divmod(length, 1)
            if length > i * 2:
                char |= coords_braille_mapping[0, j]
            if length > i * 2 + 1:
                char |= coords_braille_mapping[1, j]
        chars.append(char)

    return "".join(chr(c) for c in chars)


class Sparkbar:
    """A class that can be used to represent a sparkline-like string with up to 4 horizontal bars
    in one line.
    """

    def __init__(
        self,
        data: Iterable[float],
        min_width: int | None = None,
        max_width: int | None = None,
    ) -> None:
        self.data = tuple(data)
        self.min_width = min_width or 0
        self.max_width = max_width or shutil.get_terminal_size().columns or 80

        self._min_val = min(self.data)
        self._max_val = max(self.data)

    def update(self, data: Iterable[float]) -> None:
        """Update the sparkbar with new data."""
        new_data = tuple(data)
        assert len(new_data) == len(self.data)
        self.data = new_data

        prev_min, prev_max = self._min_val, self._max_val
        min_val = min(self.data)
        max_val = max(self.data)

        # If the new data is outside the range of the old data, we update the min/max values
        # used to calculate the bar scale. To avoid constantly updating the scale as a max
        # value increases, we bump up the max value by 25% each time there's an increase.
        # This should converge to the correct scale in a reasonable amount of time, while
        # still keeping the scale in a nice range.
        if min_val < prev_min:
            self._min_val -= min_val / 4

        if max_val > prev_max:
            self._max_val += abs(max_val) / 4

    def get_sparkbar(
        self,
        min_width: int | None = None,
        max_width: int | None = None,
        normalize: bool = True,
        scale_to_edge_values: bool = True,
    ) -> str:
        """Return the sparkbar as a string."""
        fn = get_sparkbar_normalized if normalize else get_sparkbar
        # todo - add options for adding vertical bar to start, end, 0
        return "┃" + fn(
            self.data,
            min_width=min_width if min_width is not None else self.min_width,
            max_width=max_width if max_width is not None else self.max_width,
            min_data_value=self._min_val if scale_to_edge_values else None,
            max_data_value=self._max_val if scale_to_edge_values else None,
        )

    def __str__(self) -> str:
        # Vertical line character: U+2502, aka ┃
        return self.get_sparkbar()


def get_sparkbar(
    data: Iterable[float],
    width: int=40,
    min_data_value: float | None = None,
    max_data_value: float | None = None,
    normalized: bool = True
    ) -> str:

    data = tuple(data)
    if not data:
        return "⠀" * width

    if len(data) > 4:
        raise ValueError("Sparkbar can only have up to 4 bars.")

    if normalized:
        return get_sparkbar_normalized(data, width, max_data_value, min_data_value)

    min_val = min(data)
    max_val = max(data)
    if min_data_value is not None:
        min_val = min(min_val, min_data_value)
    if max_data_value is not None:
        max_val = max(max_val, max_data_value)

    # Correct for displaying negative min_val if it's negative, but don't
    # crop the shown windows to the minimum value otherwise (i.e. if the
    # minimum value is negative, move the window so the minimum value is
    # now at the start of the line; if the miniumum value is positive, do
    # nothing, to keep the start of the line as 0).
    min_val = min_val if min_val < 0 else 0
    num_chars = width

    chars = [BRAILLE_RANGE_START] * num_chars
    for i in range(num_chars):
        # Visiting i'th character -> i*2 and i*2+1 dots
        for j, value in enumerate(data):
            if value - min_val > i * 2:
                chars[i] |= coords_braille_mapping[0, j]
            if value - min_val > i * 2 + 1:
                chars[i] |= coords_braille_mapping[1, j]
    s = "".join(chr(c) for c in chars)
    if len(s) < width:
        s = s.ljust(width, "⠀")
    if len(s) > width:
        s = s[-width:]
    return s


def get_sparkbar_normalized(
    data: Iterable[float],
    width: int=40,
    min_data_value: float | None = None,
    max_data_value: float | None = None
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

    return get_sparkbar(
        char_normalized_data,
        width=width,
        normalized=False
        )

if __name__ == "brailliant.sparkline":
    import time
    import random

    s = get_sparkbar((1, 4, 6, 3), width=5)
    # sparkbar.update([random.random() for _ in range(10)])
    # print(sparkbar)

if __name__ == "__main__":

    bar_data_large_range: list[float] = [-10, 40, 60, 0]
    bar_data_medium_range: list[float] = [1, 1, 5, 6]
    bar_data_small_range: list[float] = [0, 0, 0, 1]

    bars = [bar_data_large_range, bar_data_medium_range, bar_data_small_range]
    rates = [list(random.uniform(0, 1) for _ in range(4)) for _ in range(3)]

    sparky = Sparkbar(bars[0], min_width=10, max_width=20)

    while True:
        display = []
        sparky.update(
            (prev + math.cos(rates[0][i] * time.time() + rates[0][i] * 104) * 0.1)
            for i, prev in enumerate(sparky.data)
        )
        display.append(sparky.get_sparkbar())
        for bar, rate in zip(bars, rates):
            for i in range(len(bar)):
                bar[i] += math.cos(rate[i] * time.time() + rate[i] * 104) * 0.1

            display.append(get_sparkbar(bar, max_width=80))
            display.append(get_sparkbar_normalized(bar, max_width=80))
            display.append(get_sparkbar_normalized(bar, min_width=80, max_width=80))

        time.sleep(0.01)
        control_chrs = "\x1b[2J\x1b[H"  # Clear screen and move cursor to top left
        print(control_chrs + "\n\n".join(display))

    for bar_data in (bar_data_large_range, bar_data_medium_range, bar_data_small_range):
        print(f"get_sparkbar({repr(bar_data)})\n{get_sparkbar(bar_data)}")
        print(f"get_sparkbar_normalized({repr(bar_data)})\n{get_sparkbar_normalized(bar_data)}")

        print(
            f"get_sparkbar({repr(bar_data)}, min_width=10)\n{get_sparkbar(bar_data, min_width=10)}"
        )
        print(
            f"get_sparkbar_normalized({repr(bar_data)}, min_width=10)"
            f"\n{get_sparkbar_normalized(bar_data, min_width=10)}"
        )

        print(
            f"get_sparkbar({repr(bar_data)}, max_width=10)\n{get_sparkbar(bar_data, max_width=10)}"
        )
        print(
            f"get_sparkbar_normalized({repr(bar_data)}, max_width=10)"
            f"\n{get_sparkbar_normalized(bar_data, max_width=10)}"
        )

        print(
            f"get_sparkbar({repr(bar_data)}, min_width=10, max_width=15)"
            f"\n{get_sparkbar(bar_data, min_width=10, max_width=15)}"
        )
        print(
            f"get_sparkbar_normalized({repr(bar_data)}, min_width=10, max_width=15)"
            f"\n{get_sparkbar_normalized(bar_data, min_width=10, max_width=15)}"
        )

        print(f"=================\n")

    test_cases = [
        sparkline([1, 2, 3, 4, 5, 2, 3, 4, 3, 2, 1]),
        get_sparkbar(bar_data_large_range, min_width=40),
        get_sparkbar(bar_data_medium_range, min_width=40),
        get_sparkbar(bar_data_small_range, min_width=40),
        get_sparkbar(bar_data_large_range, max_width=20),
        get_sparkbar(bar_data_medium_range, min_width=20),
        get_sparkbar(bar_data_small_range, min_width=20),
        get_sparkbar(bar_data_large_range),
        get_sparkbar(bar_data_medium_range),
        get_sparkbar(bar_data_small_range),
        get_sparkbar_normalized(bar_data_large_range, min_width=40),
        get_sparkbar_normalized(bar_data_medium_range, min_width=40),
        get_sparkbar_normalized(bar_data_small_range, min_width=40),
        get_sparkbar_normalized(bar_data_large_range, min_width=15),
        get_sparkbar_normalized(bar_data_medium_range, min_width=15),
        get_sparkbar_normalized(bar_data_small_range, min_width=15),
        get_sparkbar_normalized(bar_data_large_range, min_width=25),
        get_sparkbar_normalized(bar_data_medium_range, min_width=25),
        get_sparkbar_normalized(bar_data_small_range, min_width=25),
        get_sparkbar_normalized(bar_data_large_range, max_width=10),
        get_sparkbar_normalized(bar_data_medium_range, max_width=10),
        get_sparkbar_normalized(bar_data_small_range, max_width=10),
        get_sparkbar_normalized(bar_data_large_range, max_width=200),
        get_sparkbar_normalized(bar_data_large_range, min_width=10, max_width=40),
    ]
    for test_case in test_cases:
        print(test_case)
