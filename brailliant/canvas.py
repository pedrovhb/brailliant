from __future__ import annotations

import itertools
import math
import operator
import timeit
from functools import partialmethod
from typing import Literal, Callable, Final, Iterable, Tuple, overload

from brailliant import coords_braille_mapping, BRAILLE_RANGE_START


def _draw_line(start: Tuple[int, int], end: Tuple[int, int]) -> Iterable[Tuple[int, int]]:
    x0, y0 = start
    x1, y1 = end

    # Calculate the change in x and y
    dx = x1 - x0
    dy = y1 - y0

    # Calculate the number of steps to take
    steps = abs(dx) if abs(dx) > abs(dy) else abs(dy)

    # Calculate the change in x and y for each step
    x_increment = dx / steps if steps else 0
    y_increment = dy / steps if steps else 0

    # Iterate over the number of steps and yield each point
    x = x0
    y = y0
    for _ in range(steps):
        yield int(round(x)), int(round(y))
        x += x_increment
        y += y_increment


def _draw_polygon(vertices: Iterable[tuple[int, int]]) -> Iterable[tuple[int, int]]:
    """Yields all points on the perimeter of a polygon with the given vertices."""
    vertices = tuple(vertices)

    with open("test.txt", "a") as f:
        print(vertices, file=f)

    for i in range(len(vertices)):
        start = vertices[i]
        end = vertices[(i + 1) % len(vertices)]
        yield from _draw_line(start, end)


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
    x0: int,
    y0: int,
    x1: int,
    y1: int,
) -> Iterable[tuple[int, int]]:
    """Yields all points between the start and end coordinates of a rectangle."""
    yield from itertools.chain(
        ((x, y0) for x in range(x0, x1)),
        ((x, y1) for x in range(x0, x1)),
        ((x0, y) for y in range(y0, y1)),
        ((x1, y) for y in range(y0, y1)),
    )


def _draw_triangle(vertices: Iterable[tuple[int, int]]) -> Iterable[tuple[int, int]]:
    """Yields all points on the perimeter of a triangle with the given vertices."""
    vertices = tuple(vertices)
    yield from _draw_line(vertices[0], vertices[1])
    yield from _draw_line(vertices[1], vertices[2])
    yield from _draw_line(vertices[2], vertices[0])


def _draw_arrow(
    start: Tuple[int, int], end_or_angle: Tuple[int, int] | float, size: int
) -> Iterable[Tuple[int, int]]:

    if isinstance(end_or_angle, (float, int)):
        end = (
            start[0] + int(size * math.cos(math.radians(end_or_angle))),
            start[1] + int(size * math.sin(math.radians(end_or_angle))),
        )
        angle = end_or_angle
    else:
        end = end_or_angle
        angle = math.degrees(math.atan2(end[1] - start[1], end[0] - start[0]))

    yield from _draw_line(start, end)
    yield from _draw_line(
        end,
        (
            end[0] + int(size * 0.4 * math.cos(math.radians(angle + 140))),
            end[1] + int(size * 0.4 * math.sin(math.radians(angle + 140))),
        ),
    )
    yield from _draw_line(
        end,
        (
            end[0] + int(size * 0.4 * math.cos(math.radians(angle - 140))),
            end[1] + int(size * 0.4 * math.sin(math.radians(angle - 140))),
        ),
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
        self._canvas = (1 << self.width_chars * self.height_chars * 8) - 1 if mode == "add" else 0
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

    @classmethod
    def from_image(
        cls, raw_bytes: bytes, img_width, img_height: int, mode: Literal["add", "clear"] = "add"
    ) -> Canvas:
        """Sets the canvas to the given image, using raw_bytes as the image data.

        The image data should be in the format of a 1-bit per pixel image, with the first byte being the top-left pixel, and the last byte being the bottom-right pixel. This is the format used by PIL.Image.tobytes(). Thus, to use this function from an image, you should use something like:

        >>> from PIL import Image
        >>> image = Image.open("image.png")
        >>> image = image.convert("1")
        >>> canvas = Canvas.from_image(image.tobytes(), image.width, image.height)

        Args:
            raw_bytes: The raw bytes of the image.
            img_width: The width of the image.
            img_height: The height of the image.
            mode: The mode to use when drawing the image. If "add", the image will be drawn as normal. If "clear", the image will be drawn with inverted colors.
        Returns:
            A new canvas with the image drawn on it.
        """

        # Image is 16 px wide - 2 cols
        # Image is 16 px tall - 4 rows
        # Each cell is 2x4 px
        # Each byte is 8 px
        # Each row is 2 bytes
        # Each cell is 4 bytes

        row_start, row_end = 0, 2
        # Generically:
        row_start, row_end = 0, img_width // 8
        col_start, col_end = 0, img_height // 4
        print(f"row_start: {row_start}, row_end: {row_end}")
        print(f"col_start: {col_start}, col_end: {col_end}")

        for j in range(4):
            for i in range(row_start, row_end, 2):
                print(f"i: {i:02}\t{raw_bytes[i]:08b}", end="")
                print()

        for i, b in enumerate(raw_bytes):
            row = i // img_width * 4
            print(f"{b:08b}", end="" if i % 2 else "\n")

        for i in raw_bytes[::img_width]:
            print(i // 8)
            print(format(i, "08"))
        for i, b in enumerate(raw_bytes):
            # row = img_height - i // (img_width // 8) - 1
            # col = i % (img_height // 8)
            col = i % (img_width // 8)
            row = img_height - i // (img_width // 8) - 1
            for j in range(8):
                if b & (1 << j):
                    x = 8 * col + j
                    y = row
                    if x < 0 or y < 0 or x >= img_width or y >= img_height:
                        continue
                    cell_x, char_x = divmod(x, 2)
                    cell_y, char_y = divmod(y, 4)
                    char = coords_braille_mapping[(char_x, char_y)]
                    char_xy = cell_y * (img_width // 2) + cell_x
                    delta |= char << char_xy * 8

        if mode == "clear":
            delta = ~delta
        return Canvas(img_width, img_height, delta)

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

    @overload
    def draw_line(
        self,
        x0_or_start: tuple[int, int],
        y0_or_end: tuple[int, int],
        x1: None,
        y1: None,
        mode: Literal["add", "clear"] = "add",
    ) -> Canvas:
        ...

    @overload
    def draw_line(
        self,
        x0_or_start: int,
        y0_or_end: int,
        x1: int,
        y1: int,
        mode: Literal["add", "clear"] = "add",
    ) -> Canvas:
        ...

    def draw_line(
        self,
        x0_or_start: tuple[int, int] | int,
        y0_or_end: tuple[int, int] | int,
        x1: int | None = None,
        y1: int | None = None,
        mode: Literal["add", "clear"] = "add",
    ) -> Canvas:

        if x1 is None and y1 is None:
            assert isinstance(x0_or_start, tuple)
            assert isinstance(y0_or_end, tuple)
            start_tup = x0_or_start
            end_tup = y0_or_end
        else:
            assert isinstance(x0_or_start, int)
            assert isinstance(y0_or_end, int)
            assert isinstance(x1, int)
            assert isinstance(y1, int)
            start_tup = (x0_or_start, y0_or_end)
            end_tup = (x1, y1)

        x0, y0 = start_tup
        x1, y1 = end_tup
        return self.with_changes(_draw_line((x0, y0), (x1, y1)), mode)

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
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        mode: Literal["add", "clear"] = "add",
    ) -> Canvas:
        """Draws a rectangle from start to end."""
        return self.with_changes(_draw_rectangle(x0, y0, x1, y1), mode)

    def draw_polygon(
        self,
        coords: Iterable[tuple[int, int]],
        mode: Literal["add", "clear"] = "add",
    ) -> Canvas:
        """Draws a polygon from the given coordinates."""
        pol = tuple(_draw_polygon(coords))
        with open("pol.txt", "a") as f:
            f.write(f"{pol}\r")
        return self.with_changes(pol, mode)

    def draw_arrow(
        self,
        start: tuple[int, int],
        end_or_angle: tuple[int, int] | float,
        size: int = 5,
        mode: Literal["add", "clear"] = "add",
    ) -> Canvas:
        """Draws an arrow from start to end."""
        return self.with_changes(_draw_arrow(start, end_or_angle, size), mode)

    def apply_other(self, other: "Canvas", operation: Callable[[int, int], int]) -> Canvas:
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
