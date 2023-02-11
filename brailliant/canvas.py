from __future__ import annotations

import functools
import itertools
import math
import operator
from enum import Enum
from functools import partialmethod
from pathlib import Path
from typing import Callable, Iterable, Iterator, Literal, overload, Tuple, TYPE_CHECKING

from brailliant import (
    BRAILLE_COLS,
    BRAILLE_RANGE_START,
    BRAILLE_ROWS,
    braille_table_str,
    coords_braille_mapping,
)

if TYPE_CHECKING:
    try:
        from PIL.Image import Image
    except ImportError:
        Image = "Image"


def _draw_line(
    start: Tuple[int, int],
    end: Tuple[int, int],
    dotting: int = 1,
) -> Iterable[Tuple[int, int]]:
    """Yields all points on the line between the start and end coordinates.

    Args:
        start: The start coordinates of the line.
        end: The end coordinates of the line.
        dotting: The spacing between dots on the line.

    Yields:
        All points on the line between the start and end coordinates.
    """
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
    x = float(x0)
    y = float(y0)
    for i in range(steps):
        if i % dotting == 0:
            yield round(x), round(y)
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


def _draw_image(image: str | Path | "Image") -> Iterator[tuple[int, int]]:
    try:
        from PIL.Image import Dither, Image, open as open_image
    except ImportError as e:
        raise ImportError(
            "ImportError while trying to import Pillow."
            "\nImage loading requires the Pillow library to be installed:"
            "\n    pip install Pillow"
        ) from e

    if isinstance(image, (str, Path)):
        image = open_image(image)

    image = image.convert("1", dither=Dither.FLOYDSTEINBERG)
    im_height = image.height
    im_width = image.width
    # todo - there's definitely a more efficient way to do this
    for i, point in enumerate(image.getdata()):
        y, x = divmod(i, im_width)
        y = im_height - y
        if point:
            yield x, y


class TextAlign(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"


class CanvasText:
    def __init__(
        self,
        x: int,
        y: int,
        text: str,
        parent: Canvas,
        alignment: TextAlign = TextAlign.LEFT,
    ):
        self.text = text
        self.x = x
        self.y = y
        self.parent = parent
        self.alignment = alignment

    def in_split_lines(self) -> Iterable[CanvasText]:
        """Yields a new CanvasText for each line of text."""
        for i, line in enumerate(self.text.splitlines()):
            yield CanvasText(
                self.x,
                self.y + (i * BRAILLE_ROWS - 1),
                line,
                self.parent,
                self.alignment,
            )

    def __repr__(self) -> str:
        return f"CanvasText({self.text!r}, {self.x}, {self.y})"


class Canvas:

    __slots__ = ("width_chars", "height_chars", "_canvas", "width", "height", "_text")

    def __init__(self, width_dots: int, height_dots: int, contents: int = 0) -> None:
        self.width = width_dots
        self.height = height_dots
        width_chars = math.ceil(width_dots / BRAILLE_COLS)
        height_chars = math.ceil(height_dots / BRAILLE_ROWS)
        self.width_chars = width_chars
        self.height_chars = height_chars
        self._canvas = contents
        self._text: list[CanvasText] = []

    @classmethod
    def with_cell_size(cls, width: int, height: int) -> Canvas:
        """Returns a new canvas with the given width and height in number of characters
        (as opposed to number of dots).
        """
        return cls(width * BRAILLE_COLS, height * BRAILLE_ROWS)

    def set_cell(self, x: int, y: int) -> Canvas:
        return self.with_changes(((x, y),), "add")

    def clear_cell(self, x: int, y: int) -> Canvas:
        return self.with_changes(((x, y),), "clear")

    def fill(self, mode: Literal["add", "clear"] = "add") -> Canvas:
        """Fills the entire canvas with the given mode."""
        self._canvas = (1 << self.width_chars * self.height_chars * 8) - 1 if mode == "add" else 0
        return self

    clear_all = partialmethod(fill, mode="clear")
    set_all = partialmethod(fill, mode="add")

    def get_str(self) -> str:
        lines = [
            "".join(
                braille_table_str[self._canvas >> i * 8 & 0xFF]
                for i in range(self.width_chars * y, self.width_chars * (y + 1))
            )
            for y in range(self.height_chars - 1, -1, -1)
        ]

        # Add text
        text_lines = itertools.chain.from_iterable(txt.in_split_lines() for txt in self._text)
        for text in text_lines:
            char_length = len(text.text)
            char_y = round(text.y / BRAILLE_ROWS)
            txt = text.text

            if char_y >= len(lines):
                continue

            if text.alignment == TextAlign.LEFT:
                char_x = text.x // BRAILLE_COLS
            elif text.alignment == TextAlign.CENTER:
                char_x = (text.x - char_length * BRAILLE_COLS // 2) // BRAILLE_COLS
            elif text.alignment == TextAlign.RIGHT:
                char_x = (text.x - char_length * BRAILLE_COLS) // BRAILLE_COLS
            else:
                raise ValueError(f"Invalid text alignment {text.alignment!r}")

            if char_x < 0:
                txt = txt[-char_x:]
                char_x = 0
            if char_x + char_length > self.width_chars:
                txt = txt[: self.width_chars - char_x]
            char_length = len(txt)

            txt_start = char_x
            txt_end = char_x + char_length
            lines[char_y] = "".join((lines[char_y][:txt_start], txt, lines[char_y][txt_end:]))

        return "\n".join(lines)

    def write_text(
        self,
        x: int,
        y: int,
        text: str,
        alignment: TextAlign = TextAlign.LEFT,
    ) -> Canvas:
        ct = CanvasText(x=x, y=y, text=text, parent=self, alignment=alignment)
        self._text.append(ct)
        return self

    def get_str_control_chars(self) -> str:
        """Returns a string with control characters to draw the canvas."""
        return self.get_str().replace("\n", "\x1b[1B\r")

    def with_changes(
        self,
        coords: Iterable[tuple[int, int]],
        mode: Literal["add", "clear"],
    ) -> Canvas:
        """Modify the canvas by setting or clearing the dots on the coordinates given by coords."""
        if mode not in ("add", "clear"):
            raise ValueError(f"Invalid mode {mode}")

        delta = 0
        for x, y in coords:

            cell_x, char_x = divmod(x, BRAILLE_COLS)
            cell_y, char_y = divmod(y, BRAILLE_ROWS)
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
        dotting: int = ...,
        mode: Literal["add", "clear"] = ...,
    ) -> Canvas:
        ...

    @overload
    def draw_line(
        self,
        x0_or_start: int,
        y0_or_end: int,
        x1: int,
        y1: int,
        dotting: int = ...,
        mode: Literal["add", "clear"] = ...,
    ) -> Canvas:
        ...

    def draw_line(
        self,
        x0_or_start: tuple[int, int] | int,
        y0_or_end: tuple[int, int] | int,
        x1: int | None = None,
        y1: int | None = None,
        dotting: int = 1,
        mode: Literal["add", "clear"] = "add",
    ) -> Canvas:

        if x1 is None and y1 is None:
            assert isinstance(x0_or_start, tuple)
            assert isinstance(y0_or_end, tuple)
            start_tup = x0_or_start
            end_tup = y0_or_end
        else:
            assert all(isinstance(i, int) for i in (x0_or_start, y0_or_end, x1, y1))
            start_tup = (x0_or_start, y0_or_end)
            end_tup = (x1, y1)

        x0, y0 = start_tup
        x1, y1 = end_tup
        return self.with_changes(_draw_line((x0, y0), (x1, y1), dotting=dotting), mode)

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
        return self.with_changes(_draw_rectangle(x0, y0, x1, y1), mode)

    def draw_polygon(
        self,
        coords: Iterable[tuple[int, int]],
        mode: Literal["add", "clear"] = "add",
    ) -> Canvas:
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
        return self.with_changes(_draw_arrow(start, end_or_angle, size), mode)

    def apply_other(self, other: "Canvas", operation: Callable[[int, int], int]) -> Canvas:
        """Apply a binary operation to the (integer value of) this canvas and another canvas, and
        return a new canvas with the result.
        """
        return Canvas(self.width, self.height, operation(self._canvas, other._canvas))

    def draw_image(
        self,
        image: str | Path | "Image",
        mode: Literal["add", "clear"] = "add",
    ) -> Canvas:
        """Draws an image on the canvas."""
        return self.with_changes(_draw_image(image), mode)

    __or__ = partialmethod(apply_other, operation=operator.or_)
    __and__ = partialmethod(apply_other, operation=operator.and_)
    __xor__ = partialmethod(apply_other, operation=operator.xor)

    def __invert__(self) -> Canvas:
        return Canvas(self.width, self.height, ~self._canvas)

    def copy(self) -> Canvas:
        return Canvas(self.width, self.height, self._canvas)

    def __str__(self) -> str:
        """Return the canvas as a string, joining chars and newlines to form rows."""
        return self.get_str()

    def __repr__(self) -> str:
        return f"Canvas({self.width}, {self.height}, {hex(self._canvas)})"


if __name__ == "__main__":

    t = tuple(chr(BRAILLE_RANGE_START | i) for i in range(256))
    et = tuple(chr(BRAILLE_RANGE_START | i).encode() for i in range(256))
    tb = tuple(BRAILLE_RANGE_START | i for i in range(256))
    print("t", t)
    print("tb", tb)

    canvas_0 = Canvas(40, 40)
    canvas_0.draw_circle((14, 4), 2, angle_step=1)
    canvas_0.draw_circle((24, 4), 6, angle_step=1)
    canvas_0.draw_circle((34, 4), 8, angle_step=1)
    canvas_0.draw_circle((24, 24), 10, angle_step=1)
    canvas_0.draw_rectangle(13, 13, 35, 35)
    print("=====")
    print(canvas_0)
    """
    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
    ⠀⠀⠀⠀⠀⠀⢸⠉⢉⣩⠽⠛⠛⠻⢭⣉⠉⢱⠀⠀
    ⠀⠀⠀⠀⠀⠀⢸⢠⠏⠀⠀⠀⠀⠀⠀⠈⢧⢸⠀⠀
    ⠀⠀⠀⠀⠀⠀⢸⡏⠀⠀⠀⠀⠀⠀⠀⠀⠈⣿⠀⠀
    ⠀⠀⠀⠀⠀⠀⢸⢧⠀⠀⠀⠀⠀⠀⠀⠀⢠⢿⠀⠀
    ⠀⠀⠀⠀⠀⠀⢸⠈⢧⣀⠀⠀⠀⠀⢀⣠⠏⢸⠀⠀
    ⠀⠀⠀⠀⠀⠀⠸⠤⠤⠬⠽⠶⠶⠾⠭⢤⣤⣼⣀⠀
    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡤⠖⠒⢦⣞⠉⠀⠀⠈⠙
    ⠀⠀⠀⠀⠀⠀⡴⠲⡄⡞⠀⠀⠀⡏⠘⡆⠀⠀⠀⠀
    ⠀⠀⠀⠀⠀⠀⠙⠚⠁⢳⡀⠀⠀⢧⣰⠃⠀⠀⠀⠀
    """

    canvas_1 = Canvas(40, 40)
    canvas_1.draw_circle((15, 15), 10)
    print("=====")
    print(canvas_1)
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

    canvas_2 = Canvas(40, 40)
    canvas_2.draw_circle((25, 25), 10)
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

    canvas_3 = canvas_1 | canvas_2
    print("=====")
    print(canvas_3)
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

    canvas_4 = Canvas(61, 91)
    canvas_4.draw_line(0, 0, 0, 90)
    canvas_4.draw_line(0, 90, 60, 90)
    canvas_4.draw_line(60, 90, 60, 0)
    canvas_4.draw_line(60, 0, 0, 0)
    canvas_4.draw_line(30, 0, 30, 90, dotting=3)
    canvas_4.write_text(30, 10, "Hello, world!")
    canvas_4.write_text(30, 20, "Hello, world!", TextAlign.CENTER)
    canvas_4.write_text(30, 30, "Hello, world!", TextAlign.RIGHT)
    canvas_4.write_text(30, 40, "Hello, kind\nworld!", TextAlign.CENTER)
    canvas_4.write_text(30, 60, "Hello,\nkind world!", TextAlign.RIGHT)
    canvas_4.write_text(30, 80, "Hello,\nkind world!", TextAlign.LEFT)
    print("=====")
    print(canvas_4)
    """
    ⡖⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⡆
    ⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇
    ⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀Hello, world!⠀⠀⡇
    ⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠂⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇
    ⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇
    ⡇⠀⠀⠀⠀⠀⠀⠀Hello, world!⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇
    ⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠂⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇
    ⡇⠀Hello, world!⡁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇
    ⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇
    ⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠂⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇
    ⡇⠀⠀⠀⠀⠀⠀⠀⠀Hello, kind⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇
    ⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀world!⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇
    ⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠂⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇
    ⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇
    ⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇
    ⡇⠀⠀⠀⠀⠀⠀⠀⠀Hello,⠂⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇
    ⡇⠀⠀⠀kind world!⡁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇
    ⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇
    ⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠂⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇
    ⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇
    ⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀Hello,⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇
    ⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀kind world!⠀⠀⠀⠀⡇
    ⣇⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣁⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⡇
    """
