from __future__ import annotations

import itertools
import math
import operator
import timeit
from functools import partialmethod
from typing import Literal, Callable, Final, Iterable

from brailliant import coords_braille_mapping, BRAILLE_RANGE_START


def _draw_line(
    start: tuple[int, int], end: tuple[int, int]
) -> Iterable[tuple[int, int]]:
    """Yields all points between the start and end coordinates using the Bresenham line algo."""
    x0, y0 = start
    x1, y1 = end
    m_new = 2 * (y1 - y0)
    slope_error_new = m_new - (x1 - x0)

    y = y0
    for x in range(x0, x1 + 1):
        yield x, y
        slope_error_new = slope_error_new + m_new
        if slope_error_new >= 0:
            y = y + 1
            slope_error_new = slope_error_new - 2 * (x1 - x0)


def _draw_arc(
    center: tuple[int, int],
    radius: int,
    start_angle: float = 0,
    end_angle: float = 360,
    angle_step: float | None = None,
) -> Iterable[tuple[int, int]]:
    """Draws a circle with the given center and radius.

    Pretty sure there's a better way to do this, but ¯\\_(ツ)_/¯
    """
    x, y = center
    start_angle = math.radians(start_angle)
    end_angle = math.radians(end_angle)
    if angle_step is None:
        angle_step = 2
    angle_step = math.radians(angle_step)
    for angle in itertools.takewhile(
        lambda a: a <= end_angle,
        itertools.count(start_angle, angle_step),
    ):
        x_offset = round(math.cos(angle) * radius)
        y_offset = round(math.sin(angle) * radius)
        yield x + x_offset, y + y_offset


def _draw_rectangle(
    start: tuple[int, int],
    end: tuple[int, int],
) -> Iterable[tuple[int, int]]:
    """Yields all points between the start and end coordinates of a rectangle."""
    x0, y0 = start
    x1, y1 = end
    yield from itertools.chain(
        ((x, y0) for x in range(x0, x1)),
        ((x, y1) for x in range(x0, x1)),
        ((x0, y) for y in range(y0, y1)),
        ((x1, y) for y in range(y0, y1)),
    )


class Canvas:

    __slots__ = ("width_chars", "height_chars", "_canvas", "width", "height")

    BRAILLE_COLS: Final[int] = 2
    BRAILLE_ROWS: Final[int] = 4

    def __init__(self, width_dots: int, height_dots: int, contents: int = 0) -> None:
        self.width = width_dots
        self.height = height_dots
        width_chars = math.ceil(width_dots / self.BRAILLE_COLS)
        height_chars = math.ceil(height_dots / self.BRAILLE_ROWS)
        self.width_chars = width_chars
        self.height_chars = height_chars
        self._canvas = contents

    def shifted(self, x: int, y: int) -> "Canvas":
        """Returns a new canvas with the given coordinates added to all coordinates."""
        canvas = self._canvas << (y * self.width_chars + x) * 8  # todo this is wrong
        return Canvas(
            self.width,
            self.height,
            canvas,
        )

    @classmethod
    def with_cell_size(cls, width: int, height: int) -> Canvas:
        return cls(width * cls.BRAILLE_COLS, height * cls.BRAILLE_ROWS)

    def to_char_xy(self, x: int, y: int) -> int:
        return y * self.width_chars + x

    def to_cell_xy(self, x: int, y: int) -> tuple[int, int]:
        return x // self.BRAILLE_COLS, y // self.BRAILLE_ROWS

    def to_cell_offset(self, x: int, y: int) -> int:
        return (y % self.BRAILLE_ROWS) * self.BRAILLE_COLS + (x % self.BRAILLE_COLS)

    def set_cell(self, x: int, y: int) -> Canvas:
        self._canvas |= 1 << y * self.width_chars + x
        return self

    def clear_cell(self, x: int, y: int) -> Canvas:
        self._canvas &= ~(1 << y * self.width_chars + x)
        return self

    def fill(self, mode: Literal["add", "clear"] = "add") -> Canvas:
        """Fills the entire canvas with the given mode."""
        self._canvas = (
            (1 << self.width_chars * self.height_chars * 8) - 1 if mode == "add" else 0
        )
        return self

    clear_all = partialmethod(fill, mode="clear")
    set_all = partialmethod(fill, mode="add")

    def get_str(self) -> str:
        t = tuple(chr(BRAILLE_RANGE_START | i) for i in range(256))
        lines = (
            "".join(
                t[self._canvas >> i * 8 & 0xFF]
                for i in range(self.width_chars * y, self.width_chars * (y + 1))
            )
            for y in range(self.height_chars - 1, -1, -1)
        )
        return "\n".join(lines)

    # t = tuple(chr(BRAILLE_RANGE_START | i) for i in range(256))
    # return "\r\n".join(
    #     "".join(
    #         chr(BRAILLE_RANGE_START | self._canvas >> (j * self.width_chars + i) & 0xFF)
    #         for i in range(self.width_chars)
    #     )
    #     for j in range(self.height_chars)
    # )
    # lines = [
    #     "\r\033[1B".join(
    #         t[self._canvas >> (i * self.width_chars + i) & 0xFF]
    #         for i in range(self.width_chars)
    #     )
    #     for _ in range(self.height_chars)
    # ]
    # print(len(lines[0]))
    # return "\n".join(lines)

    def get_str_control_chars(self) -> str:
        """Returns a string with control characters to draw the canvas."""
        return self.get_str().replace("\n", "\x1b[1B\r")

    def with_changes(
        self,
        coords: Iterable[tuple[int, int]],
        mode: Literal["add", "clear"],
    ) -> Canvas:
        """Returns a new canvas with the given coordinates modified according to the mode."""
        if mode not in ("add", "clear"):
            raise ValueError(f"Invalid mode {mode}")

        delta = 0
        for x, y in coords:

            if (
                x < 0
                or y < 0
                or x >= self.width_chars * self.BRAILLE_COLS
                or y >= self.height_chars * self.BRAILLE_ROWS
            ):
                continue

            cell_x, char_x = divmod(x, self.BRAILLE_COLS)
            cell_y, char_y = divmod(y, self.BRAILLE_ROWS)
            char = coords_braille_mapping[(char_x, char_y)]
            char_xy = cell_y * self.width_chars + cell_x
            delta |= char << char_xy * 8

        if mode == "add":
            self._canvas |= delta
        else:
            self._canvas &= ~delta

        return self

    def draw_line(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        mode: Literal["add", "clear"] = "add",
    ) -> Canvas:
        """Draw a line from start to end."""
        return self.with_changes(_draw_line(start, end), mode)

    def draw_arc(
        self,
        center: tuple[int, int],
        radius: int,
        start_angle: float = 0,
        end_angle: float = 360,
        angle_step: float | None = None,
        mode: Literal["add", "clear"] = "add",
    ) -> Canvas:
        """Draws a circle with the given center and radius."""
        return self.with_changes(
            _draw_arc(center, radius, start_angle, end_angle, angle_step),
            mode,
        )

    def draw_circle(
        self,
        center: tuple[int, int],
        radius: int,
        angle_step: float = 1,
        mode: Literal["add", "clear"] = "add",
    ) -> Canvas:
        return self.draw_arc(
            center=center,
            radius=radius,
            start_angle=0,
            end_angle=360,
            angle_step=angle_step,
            mode=mode,
        )

    def draw_rectangle(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        mode: Literal["add", "clear"] = "add",
    ) -> Canvas:
        """Draws a rectangle from start to end."""
        return self.with_changes(_draw_rectangle(start, end), mode)

    def apply_other(
        self, other: "Canvas", operation: Callable[[int, int], int]
    ) -> Canvas:
        """Apply a binary operation to the (integer value of) this canvas and another canvas, and
        return a new canvas with the result.
        """
        return Canvas(self.width, self.height, operation(self._canvas, other._canvas))

    __or__ = partialmethod(apply_other, operation=operator.or_)
    __and__ = partialmethod(apply_other, operation=operator.and_)
    __xor__ = partialmethod(apply_other, operation=operator.xor)

    def __invert__(self) -> "Canvas":
        return Canvas(self.width, self.height, ~self._canvas)

    def copy(self) -> "Canvas":
        return Canvas(self.width, self.height, self._canvas)

    def __str__(self) -> str:
        """Return the canvas as a string, joining chars and newlines to form rows."""
        return self.get_str()

    def __repr__(self) -> str:
        return f"Canvas({self.width}, {self.height}, {hex(self._canvas)})"


if __name__ == "__live_coding__":
    # c = Canvas(10, 10)
    # c.draw_circle((4, 4), 2, angle_step=15)
    # c.get_str()
    pass

elif __name__ == "__main__":

    t = tuple(chr(BRAILLE_RANGE_START | i) for i in range(256))
    et = tuple(chr(BRAILLE_RANGE_START | i).encode() for i in range(256))
    tb = tuple(BRAILLE_RANGE_START | i for i in range(256))
    print("t", t)
    print("tb", tb)

    c = Canvas(40, 40)
    c.draw_circle((14, 4), 2, angle_step=1)
    c.draw_circle((24, 4), 6, angle_step=1)
    c.draw_circle((34, 4), 8, angle_step=1)
    c.draw_circle((24, 24), 10, angle_step=1)
    print(c.get_str())
    print("\n\n")

    print(f"Time to run get_str: {timeit.timeit(c.get_str, number=1000)}")
    print(
        f"Time to run get_str_control_chars: {timeit.timeit(c.get_str_control_chars, number=1000)}"
    )

    canvas = Canvas(40, 40)
    canvas.draw_circle((15, 15), 10)

    canvas_2 = Canvas(40, 40)
    canvas_2.draw_circle((25, 25), 10)

    print("=====")
    print(canvas)
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

    print("=====")
    print(canvas_2)
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

    print("=====")
    print(canvas | canvas_2)
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
    print("=====")
