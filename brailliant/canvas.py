from __future__ import annotations

from itertools import chain, count, takewhile
import math
import operator
from enum import Enum
from fractions import Fraction
from functools import partialmethod
from pathlib import Path
from typing import (
    Callable,
    Iterable,
    Iterator,
    Literal,
    Tuple,
    TYPE_CHECKING,
    Dict,
    NamedTuple,
)

from bitarray import bitarray

from brailliant import BRAILLE_COLS, BRAILLE_ROWS, braille_table_bitarray

if TYPE_CHECKING:
    try:
        from PIL.Image import Image, ImageDraw, ImageFont
    except ImportError:
        Image = "Image"
        ImageDraw = "ImageDraw"
        ImageFont = "ImageFont"


class DrawMode(str, Enum):
    """The mode to draw in."""

    ADD = "add"
    CLEAR = "clear"


def _draw_line(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    dotting: int = 1,
) -> Iterator[Tuple[int, int]]:
    """Yields all points on the line between the start and end coordinates.

    Args:
        start_x: The x value for the starting point of the line.
        start_y: The y value for the starting point of the line.
        end_x: The x value for the ending point of the line.
        end_y: The y value for the ending point of the line.

    Yields:
        All points on the line between the start and end coordinates.
    """
    # Calculate the change in x and y
    dx = end_x - start_x
    dy = end_y - start_y

    # Calculate the number of steps to take
    steps = abs(dx) if abs(dx) > abs(dy) else abs(dy)

    # Calculate the change in x and y for each step
    x_increment = dx / steps if steps else 0
    y_increment = dy / steps if steps else 0

    # Iterate over the number of steps and yield each point
    x = float(start_x)
    y = float(start_y)
    for i in range(steps):
        if i % dotting == 0:
            yield round(x), round(y)
        x += x_increment
        y += y_increment


def _regular_polygon_vertices(
    center_x: int,
    center_y: int,
    radius: int,
    sides: int = 5,
    rotation: float = 0,
) -> list[Tuple[int, int]]:
    """
    Returns the vertices of a regular polygon.

    Args:
        center_x: The x coordinate of the center of the polygon.
        center_y: The y coordinate of the center of the polygon.
        radius: The radius of the polygon.
        sides: The number of sides the polygon should have.
        rotation: The rotation of the polygon in degrees.

    Returns:

    """
    coordinates = []
    angle_step = Fraction(360, sides)

    # Ensure the rotation 0 polygon always has a horizontal bottom -
    # start drawing the first vertice at 90 + angle_step / 2
    rotation -= 90 + Fraction(angle_step, 2)

    rotation = math.radians(rotation)
    angle_step = math.radians(angle_step)

    for i in range(sides):
        x = int(math.cos(i * angle_step + rotation) * radius) + center_x
        y = int(math.sin(i * angle_step + rotation) * radius) + center_y
        coordinates.append((x, y))
    return coordinates


def _fill_convex_outline(outline: Iterable[Tuple[int, int]]):
    # Store the min and max x values for each y value, so we can fill in all
    # the pixels between them
    min_max_x: Dict[int, Tuple[int, int]] = {}
    for xy in outline:
        x, y = xy
        if y not in min_max_x:
            min_max_x[y] = x, x
            continue
        min_x = min(x, min_max_x[y][0])
        max_x = max(x, min_max_x[y][1])
        min_max_x[y] = min_x, max_x

    for y, (min_x, max_x) in min_max_x.items():
        for x in range(min_x, max_x + 1):
            yield x, y


def _draw_polygon(
    vertices: Iterable[Tuple[int, int]],
    filled: bool = False,
) -> Iterator[Tuple[int, int]]:
    """Yields all points on the perimeter of a polygon with the given vertices."""

    if filled:
        yield from _fill_convex_outline(_draw_polygon(vertices, filled=False))
    else:
        vertices = tuple(vertices)
        for i in range(len(vertices)):
            start = vertices[i]
            end = vertices[(i + 1) % len(vertices)]
            yield from _draw_line(*start, *end)


def _draw_arc(
    x: int,
    y: int,
    radius: int,
    filled: bool = False,
    start_angle: float = 0,
    end_angle: float = 360,
    angle_step: float | None = None,
) -> Iterator[Tuple[int, int]]:
    """Draws a circle with the given center and radius.

    Pretty sure there's a better way to do this, but ¯\\_(ツ)_/¯
    """

    if filled:
        it = _draw_arc(
            x,
            y,
            radius,
            filled=False,
            start_angle=start_angle,
            end_angle=end_angle,
            angle_step=angle_step,
        )

        if start_angle % 360 != end_angle % 360:

            def _pizza_slice():
                prev_point = next(it)
                yield from _draw_line(x, y, *prev_point)
                for point in it:
                    yield point
                    prev_point = point
                yield from _draw_line(*prev_point, x, y)
                # todo - implement filled arcs

            yield from _pizza_slice()

        else:
            yield from _fill_convex_outline(it)
    else:
        start_angle = math.radians(start_angle)
        end_angle = math.radians(end_angle)
        if angle_step is None:
            angle_step = 2
        angle_step = math.radians(angle_step)
        for angle in takewhile(
            lambda a: a <= end_angle,
            count(start_angle, angle_step),
        ):
            x_offset = round(math.cos(angle) * radius)
            y_offset = round(math.sin(angle) * radius)
            yield x + x_offset, y + y_offset


class _LineDefinition(NamedTuple):
    start_x: int
    start_y: int
    end_x: int
    end_y: int


def _draw_rectangle(
    x: int,
    y: int,
    width: int,
    height: int,
    filled: bool = False,
    rotation: float = 0,
    anchor_x: float = 0,
    anchor_y: float = 0,
) -> Iterator[Tuple[int, int]]:
    # Calculate the angle in radians
    angle = math.radians(rotation % 360)
    cos = math.cos(angle)
    sin = math.sin(angle)

    # Anchor point is the point around which the rectangle is rotated. Here we convert it to
    # an absolute position rather than a relative position to the width and height.
    anchor_x = width * anchor_x
    anchor_y = height * anchor_y

    # Calculate the corners of the rectangle
    corners = [
        (x - anchor_x, y - anchor_y),
        (x + width - anchor_x, y - anchor_y),
        (x + width - anchor_x, y + height - anchor_y),
        (x - anchor_x, y + height - anchor_y),
    ]

    # Rotate the corners
    corners = [
        (
            round(x * cos - y * sin + width / 2),
            round(x * sin + y * cos + height / 2),
        )
        for x, y in corners
    ]

    yield from _draw_polygon(corners, filled=filled)


def _draw_arrow(
    start: Tuple[int, int], end_or_angle: Tuple[int, int] | float, size: int
) -> Iterator[Tuple[int, int]]:
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


def _font_text_to_image(text: str, width: int, font_path: Path | str | None = None) -> Image:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as e:
        raise ImportError(
            "ImportError while trying to import Pillow."
            "\nImage loading requires the Pillow library to be installed:"
            "\n    pip install Pillow"
        ) from e

    # todo - allow text rotation

    font_path = str(font_path) if font_path else None

    # create an ImageDraw object to measure the text size
    measure_draw = ImageDraw.Draw(Image.new("RGB", (0, 0)))
    measure_draw.fontmode = "1"

    font_size = 100
    left = 0
    right = None

    # Do a binary search for the right font size
    while True:
        font = ImageFont.truetype(font_path, size=font_size)
        bbox = measure_draw.multiline_textbbox((0, 0), text, font)
        text_width = bbox[2] - bbox[0]
        if text_width == width:
            break
        elif text_width < width:
            left = font_size
            if right is None:
                right = font_size * 2
            font_size = font_size * 2 if right is None else (font_size + right) // 2
        else:
            right = font_size
            font_size = (font_size + left) // 2
        if left == right or (right is not None and left + 1 == right):
            font = ImageFont.truetype(font_path, size=left)
            bbox = measure_draw.multiline_textbbox((0, 0), text, font)
            break

    # Create a new image with black background
    image = Image.new("RGB", (width, bbox[3]), color="black")

    # Create an ImageDraw object to draw on the image
    draw = ImageDraw.Draw(image)
    draw.fontmode = "1"  # Disable antialiasing

    # Draw the text on the image
    draw.multiline_text((0, 0), text, fill="white", font=font)

    return image.crop(bbox)


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

    def in_split_lines(self) -> Iterator[CanvasText]:
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


def get_char(grid: bitarray, x: int, y: int, w: int) -> bitarray:
    """Get a single braille character from a grid of characters."""
    char = bitarray(8)
    for i in range(4):
        start = (y * 4 + i) * w + x * 2
        end = start + 2
        char[2 * i : 2 * i + 2] = grid[start:end]
    return char


class Canvas:
    __slots__ = ("width_chars", "height_chars", "_canvas", "width", "height", "_text")

    def __init__(self, width_dots: int, height_dots: int, contents: bitarray | None = None) -> None:
        # todo - width/height are being rounded with little indication that they are,
        #  which could be confusing. This simplifies things a lot though, so perhaps
        #  the solution is to just hide away this detail (or have it be well documented)

        self.width_chars = (width_dots + BRAILLE_COLS - 1) // BRAILLE_COLS
        self.height_chars = (height_dots + BRAILLE_ROWS - 1) // BRAILLE_ROWS

        self.width = self.width_chars * BRAILLE_COLS
        self.height = self.height_chars * BRAILLE_ROWS

        self._canvas: bitarray

        if contents is None:
            self._canvas = bitarray(self.width * self.height)
            self._canvas.setall(0)
        else:
            self._canvas = contents

        self._text: list[CanvasText] = []

    @classmethod
    def with_chars_size(cls, width: int, height: int) -> Canvas:
        """Returns a new canvas with the given width and height in number of characters
        (as opposed to number of dots).
        """
        return cls(width * BRAILLE_COLS, height * BRAILLE_ROWS)

    def set_cell(self, x: int, y: int) -> Canvas:
        """Sets the cell at the given coordinates to be filled."""
        self._canvas[(self.height - y - 1) * self.width + x] = 1
        return self

    def clear_cell(self, x: int, y: int) -> Canvas:
        """Sets the cell at the given coordinates to be empty."""
        self._canvas[(self.height - y - 1) * self.width + x] = 0
        return self

    def fill(self, mode: DrawMode = DrawMode.ADD) -> Canvas:
        """Fills the entire canvas with the given mode."""
        self._canvas.setall(1 if mode == "add" else 0)
        return self

    def invert(self) -> Canvas:
        """Inverts the entire canvas."""
        self._canvas.invert()
        return self

    def clear_all(self) -> Canvas:
        """Clears the entire canvas."""
        self._canvas.setall(0)
        return self

    def set_all(self) -> Canvas:
        """Sets the entire canvas."""
        self._canvas.setall(1)
        return self

    def get_str(self) -> str:
        lines = []
        for y in range(self.height_chars):
            line = bitarray()
            for x in range(self.width_chars):
                char = get_char(self._canvas, x, y, self.width)
                line.extend(char)

            lines.append(b"".join(line.decode(braille_table_bitarray)).decode("utf-8"))

        # Add text
        text_lines = chain.from_iterable(txt.in_split_lines() for txt in self._text)
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

    def with_changes(
        self,
        coords: Iterable[Tuple[int, int]],
        mode: DrawMode = DrawMode.ADD,
    ) -> Canvas:
        """Modify the canvas by setting or clearing the dots on the coordinates given by coords."""
        if mode not in ("add", "clear"):
            raise ValueError(f"Invalid mode {mode}")

        val = 1 if mode == "add" else 0
        w, h = self.width, self.height
        for x, y in coords:
            if 0 <= x < w and 0 <= y < h:
                self._canvas[(h - y - 1) * w + x] = val
        return self

    def draw_line(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        dotting: int = 1,
        mode: DrawMode = DrawMode.ADD,
    ) -> Canvas:
        return self.with_changes(_draw_line(start_x, start_y, end_x, end_y, dotting=dotting), mode)

    def draw_polygon(
        self,
        center_x: int,
        center_y: int,
        sides: int,
        radius: int,
        rotation: float = 0,
        filled: bool = False,
        mode: DrawMode = DrawMode.ADD,
    ) -> Canvas:
        vertices = _regular_polygon_vertices(
            center_x,
            center_y,
            sides=sides,
            radius=radius,
            rotation=rotation,
        )
        return self.with_changes(_draw_polygon(vertices, filled=filled), mode=mode)

    def draw_arc(
        self,
        x: int,
        y: int,
        radius: int,
        start_angle: float = 0,
        end_angle: float = 360,
        angle_step: float | None = None,
        filled: bool = False,
        mode: DrawMode = DrawMode.ADD,
    ) -> Canvas:
        """Draws a circle with the given center and radius."""
        return self.with_changes(
            _draw_arc(x, y, radius, filled, start_angle, end_angle, angle_step),
            mode,
        )

    def draw_circle(
        self,
        center_x: int,
        center_y: int,
        radius: int,
        filled: bool = False,
        angle_step: float = 1,
        mode: DrawMode = DrawMode.ADD,
    ) -> Canvas:
        return self.draw_arc(
            x=center_x,
            y=center_y,
            radius=radius,
            start_angle=0,
            end_angle=360,
            angle_step=angle_step,
            filled=filled,
            mode=mode,
        )

    def draw_rectangle(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        rotation: float = 0,
        filled: bool = False,
        anchor_x: float = 0.5,
        anchor_y: float = 0.5,
        mode: DrawMode = DrawMode.ADD,
    ) -> Canvas:
        changes = _draw_rectangle(
            x=x,
            y=y,
            width=width,
            height=height,
            rotation=rotation,
            filled=filled,
            anchor_x=anchor_x,
            anchor_y=anchor_y,
        )
        return self.with_changes(changes, mode)

    def draw_border(
        self,
        dotting: int = 1,
        margin: int = 2,
        mode: DrawMode = DrawMode.ADD,
    ) -> Canvas:
        # Opposite mode for margins
        margin_mode = "clear" if mode == "add" else "add"

        self.draw_rectangle(
            x=0,
            y=0,
            width=margin,
            height=self.height,
            filled=True,
            mode=margin_mode,
        )
        self.draw_rectangle(
            x=self.width - margin,
            y=0,
            width=margin,
            height=self.height,
            filled=True,
            mode=margin_mode,
        )
        self.draw_rectangle(
            x=0,
            y=0,
            width=self.width,
            height=margin,
            filled=True,
            mode=margin_mode,
        )
        self.draw_rectangle(
            x=0,
            y=self.height - margin,
            width=self.width,
            height=margin,
            filled=True,
            mode=margin_mode,
        )

        if dotting:
            # Draw the border
            self.draw_line(
                margin,
                margin,
                self.width - margin,
                margin,
                dotting=dotting,
            )
            self.draw_line(
                self.width - margin,
                margin,
                self.width - margin,
                self.height - margin,
                dotting=dotting,
            )
            self.draw_line(
                self.width - margin,
                self.height - margin,
                margin,
                self.height - margin,
                dotting=dotting,
            )
            self.draw_line(
                margin,
                self.height - margin,
                margin,
                margin,
                dotting=dotting,
            )

        return self

    def draw_grid(
        self,
        x_spacing: int,
        y_spacing: int,
        dotting: int = 1,
        mode: DrawMode = DrawMode.ADD,
    ) -> Canvas:
        lines = chain(
            *(
                _draw_line(x, 0, x, self.height, dotting=dotting)
                for x in range(0, self.width, x_spacing)
            ),
            *(
                _draw_line(0, y, self.width, y, dotting=dotting)
                for y in range(0, self.height, y_spacing)
            ),
        )
        return self.with_changes(lines, mode)

    def draw_arrow(
        self,
        start: Tuple[int, int],
        end_or_angle: Tuple[int, int] | float,
        size: int = 5,
        mode: DrawMode = DrawMode.ADD,
    ) -> Canvas:
        return self.with_changes(_draw_arrow(start, end_or_angle, size), mode)

    def apply_other(
        self, other: "Canvas", operation: Callable[[bitarray, bitarray], bitarray]
    ) -> Canvas:
        """Apply a binary operation to the (integer value of) this canvas and another canvas, and
        return a new canvas with the result.
        """
        ba = operation(self._canvas, other._canvas)
        return Canvas(self.width, self.height, ba)

    def draw_image(
        self,
        image: str | Path | "Image",
        x: int = 0,
        y: int = 0,
        resize: Literal["cover"]
        | Tuple[int, int]
        | Tuple[int, None]
        | Tuple[None, int]
        | None = None,
        mode: DrawMode = DrawMode.ADD,
        dither: bool = True,
    ) -> Canvas:
        """Draw an image on the canvas.

        Args:
            image: The image to draw. Can be a path to an image file as a string or Path,
                or a PIL.Image.Image
            x: The x coordinate of the bottom left corner of the image.
            y: The y coordinate of the bottom left corner of the image.
            resize: How to resize the image. Can be one of:
                - "cover": Resize the image to cover the entire canvas, cropping the image if
                    necessary.
                - (width, height): Resize the image to the given width and height.
                - (width, None): Resize the image to the given width, keeping the aspect ratio.
                - (None, height): Resize the image to the given height, keeping the aspect ratio.
                - None: Do not resize the image.
            mode: The draw mode to use.
            dither: Whether to dither the image when resizing it.

        Returns:
            The canvas with the image drawn on it.
        """
        try:
            from PIL.Image import Dither, open as open_image, Resampling
            import PIL.Image
        except ImportError as e:
            raise ImportError(
                "ImportError while trying to import Pillow."
                "\nImage loading requires the Pillow library to be installed:"
                "\n    pip install Pillow"
            ) from e

        if isinstance(image, (str, Path)):
            image = open_image(image)

        if resize is not None:
            resample = Resampling.LANCZOS
            if resize == "cover":
                image = image.resize((self.width, self.height), resample=resample)
            else:
                w, h = resize
                if w is None:
                    w = int(image.width * h / image.height)
                elif h is None:
                    h = int(image.height * w / image.width)
                image = image.resize((w, h), resample=resample)

        final_img = PIL.Image.new(
            mode=image.mode,
            size=(self.width, self.height),
            color=0 if mode == "clear" else 255,
        )
        final_img.paste(image, (x, y))
        final_img = final_img.convert("1", dither=Dither.FLOYDSTEINBERG if dither else Dither.NONE)

        final_img.save("final_img.png")

        im_bitarray = bitarray((1 if px else 0 for px in final_img.getdata(0)))
        if mode == "clear":
            im_bitarray = ~im_bitarray
            self._canvas &= im_bitarray
        else:
            self._canvas |= im_bitarray

        return self

    def draw_font_text(
        self,
        text: str,
        font_path: Path | str,
        width: int,
        x: int = 0,
        y: int = 0,
    ) -> Canvas:
        """Draws text using braille characters with the given font.

        Args:
            text: The text to draw.
            font_path: The path to the font file.
            width: The width of the text in pixels.
            x: The x coordinate of the bottom left corner of the text.
            y: The y coordinate of the bottom left corner of the text.

        Returns:
            The canvas with the text drawn on it.
        """
        print(f"Drawing text {text!r} with font {font_path!r} and width {width}")
        return self.draw_image(
            _font_text_to_image(text=text, font_path=font_path, width=width),
            dither=False,
            x=x,
            y=y,
        )

    @classmethod
    def from_font_text(cls, text: str, font_path: Path | str, width: int) -> Canvas:
        """Creates a new canvas with the given text drawn using braille characters."""
        img = _font_text_to_image(text=text, font_path=font_path, width=width)
        return cls(img.width, img.height).draw_image(img, dither=False)

    __or__ = partialmethod(apply_other, operation=operator.or_)
    __and__ = partialmethod(apply_other, operation=operator.and_)
    __xor__ = partialmethod(apply_other, operation=operator.xor)
    __invert__ = invert

    def copy(self) -> Canvas:
        return Canvas(self.width, self.height, self._canvas.copy())

    def __str__(self) -> str:
        """Return the canvas as a string, joining chars and newlines to form rows."""
        return self.get_str()

    def __repr__(self) -> str:
        return f"Canvas({self.width}, {self.height}, {hex(self._canvas)})"

    def __eq__(self, other):
        if isinstance(other, Canvas) and self._canvas == other._canvas:
            return True
        return False


if __name__ == "__main__":

    canvas_t = Canvas(10, 10)
    canvas_t.set_cell(0, 0)
    canvas_t.set_cell(0, 1)
    canvas_t.set_cell(1, 0)
    canvas_t.set_cell(2, 0)
    canvas_t.draw_line(0, 0, 9, 9)
    print(canvas_t)

    canvas_0 = Canvas(40, 40)
    canvas_0.draw_circle(14, 4, 2, False, angle_step=1)
    canvas_0.draw_circle(24, 4, 6, False, angle_step=1)
    canvas_0.draw_circle(34, 4, 8, False, angle_step=1)
    canvas_0.draw_circle(24, 24, 10, False, angle_step=1)
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
    canvas_1.draw_circle(15, 15, 10, False)
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
    canvas_2.draw_circle(25, 25, 10, False)
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

    canvas_5 = Canvas(100, 100)

    canvas_5.draw_polygon(50, 50, 4, 20, 0)
    canvas_5.draw_polygon(50, 50, 4, 20, 45)
    print(canvas_5)

    canvas_5.clear_all()
    canvas_5.draw_polygon(50, 50, 5, 35, 0, filled=True, mode=DrawMode.ADD)
    canvas_5.draw_polygon(50, 50, 5, 30, 0, filled=True, mode=DrawMode.CLEAR)
    canvas_5.draw_polygon(50, 50, 5, 25, 0, filled=False)

    canvas_5.draw_circle(20, 20, 10, filled=True)
    canvas_5.draw_arc(80, 80, 10, start_angle=90, end_angle=380, filled=False)
    canvas_5.draw_arc(20, 80, 10, start_angle=90, end_angle=380, filled=True)

    print(canvas_5)

    canvas_6 = Canvas(100, 100)
    canvas_6.draw_grid(10, 10, dotting=10, mode=DrawMode.ADD)
    canvas_6.draw_border(1, 1, mode=DrawMode.ADD)

    canvas_6.draw_rectangle(10, 10, 20, 20, filled=True, mode=DrawMode.ADD)
    canvas_6.draw_rectangle(10, 40, 20, 20, filled=False, mode=DrawMode.ADD)
    canvas_6.draw_rectangle(
        40,
        int(10 + 10 * math.sqrt(2)),
        20,
        20,
        rotation=45,
        anchor_x=0,
        anchor_y=0,
        filled=True,
        mode=DrawMode.ADD,
    )

    canvas_6.draw_rectangle(40, 60, 20, 20, filled=False)
    canvas_6.draw_rectangle(80, 20, 20, 40, rotation=5, filled=False)
    canvas_6.draw_rectangle(80, 80, 20, 20, rotation=45, filled=False)
    print(canvas_6)
