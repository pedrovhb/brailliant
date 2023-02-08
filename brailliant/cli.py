import argparse
import math
import shutil
import sys
from functools import partial
from pathlib import Path
from typing import Literal

from brailliant import sparkline
from brailliant.base import BRAILLE_COLS, BRAILLE_ROWS, braille_table_str
from brailliant.canvas import Canvas

try:
    import PIL
    from PIL import ImageChops, ImageFilter

    from PIL.Image import Dither, Image, open as image_open, Resampling
except ImportError:
    raise ImportError(
        "Image display requires the Pillow library. Please install it with 'pip install Pillow'."
    )


def display_braille_image() -> None:

    parser = argparse.ArgumentParser(
        prog="brailliant",
        description="Convert images to braille text.",
        usage=(
            "Convert an image to braille, displaying it in the terminal or saving it to a file.\n\n"
            "By default, the image is resized to fit the terminal window while maintaining the "
            "aspect ratio. A specific size can be specified with the --size option. \n\n"
            "To write the result to a file, use the --output option, or redirect output to it.\n\n"
            "  Examples:\n\n"
            "    Convert an image to braille and display it in the terminal:\n"
            "    $ python braille.py input.png\n\n"
            "    # Convert an image to braille and save it to a file:\n"
            "    $ python braille.py input.png -o output.txt\n\n"
            "    # Convert an image to a specific size and display it in the terminal:\n"
            "    $ python braille.py input.png -s 100 100\n\n"
            "    # Convert an image to braille without dithering and display it in the terminal:\n"
            "    $ python braille.py input.png --no-dither\n\n"
            "    # Convert an image to braille and save it to a file, displaying verbose output:\n"
            "    $ python braille.py input.png -o output.txt -v\n"
        ),
        add_help=True,
    )
    parser.add_argument(
        "input",
        type=Path,
        help="The input image.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        type=Path,
        help="Output text file. If not specified, output will be written to stdout.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Output logs verbosely",
    )
    parser.add_argument(
        "-s",
        "--size",
        type=int,
        nargs=2,
        default=None,
        help="size of the output image",
    )
    parser.add_argument(
        "-k",
        "--keep-ratio",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="keep the aspect ratio of the image",
    )
    parser.add_argument(
        "-c",
        "--color",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="use color",
    )

    args = parser.parse_args()
    log = partial(print, file=sys.stderr) if args.verbose else lambda message: None

    log(f"Loading image {args.input}")
    image = image_open(args.input)

    term_size = shutil.get_terminal_size()
    size = args.size if args.size else (term_size[0] * BRAILLE_COLS, term_size[1] * BRAILLE_ROWS)
    log(f"Converting image to braille with size {'x'.join(map(str, size))}")

    result_text = image_to_braille(
        image=image,
        size=size,
        keep_ratio=args.keep_ratio,
        color=args.color,
    )

    if (output_file := args.output) is not None:
        log(f"Writing output to {output_file}")
        with output_file.open("w") as f:
            f.write(result_text)
        log(f"Output written to {output_file}")
    else:
        log(f"Writing output to {output_file}")
        sys.stdout.write(result_text)


def image_to_braille(
    image: Image,
    size: tuple[int, int],
    keep_ratio: bool = True,
    color: bool = False,
) -> str:
    if keep_ratio:
        image = image.copy()  # don't modify the original image
        image.thumbnail(size)
    else:
        image = image.resize(size)

    if color:
        image_bg = image.reduce((BRAILLE_COLS, BRAILLE_ROWS))
        canvas = Canvas(image.width, image.height)
        canvas.draw_image(
            image.filter(ImageFilter.EDGE_ENHANCE_MORE).filter(ImageFilter.EDGE_ENHANCE_MORE)
        )
        result_text = str(canvas)
        chars = []
        for y, line in enumerate(result_text.splitlines(keepends=False)):
            for x, ch in enumerate(line):

                if x >= image_bg.width or y >= image_bg.height:
                    bg_r, bg_g, bg_b = (0, 0, 0)
                else:
                    bg_r, bg_g, bg_b = image_bg.getpixel((x, y))

                if x >= image.width * BRAILLE_ROWS or y >= image_bg.height * BRAILLE_COLS:
                    fg_r, fg_g, fg_b = (0, 0, 0)
                else:
                    fg_r, fg_g, fg_b = image.getpixel((x * BRAILLE_COLS, y * BRAILLE_ROWS))

                code_bg = f"48;2;{bg_r};{bg_g};{bg_b}"
                code_fg = f"38;2;{fg_r};{fg_g};{fg_b}"
                chars.append(f"\033[{code_bg};{code_fg}m{ch}")
            chars.append("\033[0m\n")
        return "".join(chars) + "\033[0m\n"
    else:
        image_dithered = image.filter(ImageFilter.EDGE_ENHANCE_MORE)
        image_dithered = image_dithered.convert("1", dither=Dither.FLOYDSTEINBERG)
        canvas = Canvas(image_dithered.width, image_dithered.height)
        canvas.draw_image(image_dithered)

        return str(canvas) + "\n"


def bin_to_braille(
    bs: bytes,
    show_ascii: bool = False,
) -> str:
    """Return a braille string representation of a byte string.

    Each character returned represents one byte. If show_ascii is True, the
    character will be replaced with the ASCII representation of the byte if
    it is printable.

    Args:
        bs: The byte string to convert.
        show_ascii: Whether to show the ASCII representation of the byte if it is printable.

    Returns:
        A string representation of the byte string.
    """

    result_chars = [
        ch
        if (ch := chr(b_val)).isascii() and show_ascii and ch.isprintable()
        else braille_table_str[b_val]
        for b_val in bs
    ]
    return "".join(result_chars)  # todo - add to argparse


def display_braille_repr() -> None:
    """Display a braille string representation of a byte string."""
    parser = argparse.ArgumentParser()
    display_group = parser.add_mutually_exclusive_group()
    # display_group.add_argument(
    #     "-r",
    #     "--row",
    #     action="store_true",
    #     help="Display the braille representation in rows",
    # )
    display_group.add_argument(
        "-a",
        "--ascii",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Show the ASCII representation of the byte if it is printable",
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Input file to convert to braille",
    )
    parser.add_argument(
        "-s",
        "--separate",
        type=int,
        default=False,
        help="Separate the braille representation with spaces every n bytes",
    )

    args = parser.parse_args()
    show_ascii = args.ascii
    bs = args.input.read_bytes()

    for i, b in enumerate(bs):
        if show_ascii and chr(b).isprintable():
            sys.stdout.write(chr(b))
        else:
            sys.stdout.write(braille_table_str[b])
        if args.separate and (i + 1) % args.separate == 0:
            sys.stdout.write(" ")


def display_sparkline():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-w",
        "--width",
        type=int,
        default=80,
        help="Width of the sparkline",
    )
    parser.add_argument(
        "-m",
        "--max",
        type=int,
        default=None,
        help="Maximum value of the sparkline",
    )
    parser.add_argument(
        "-n",
        "--min",
        type=int,
        default=None,
        help="Minimum value of the sparkline",
    )
    parser.add_argument(
        "-c",
        "--color",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Color the sparkline",
    )
    parser.add_argument(
        "-f",
        "--filled",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fill the sparkline",
    )
    parser.add_argument(
        "-l",
        "--log-scale",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Use a log scale for the sparkline",
    )
    parser.add_argument(
        "-t",
        "--title",
        type=str,
        default=None,
        help="Title of the sparkline",
    )

    args = parser.parse_args()
    title = args.title if args.title is not None else ""

    stdin = sys.stdin.buffer
    values = []
    for line in stdin:
        line = line.decode("utf-8")
        line = line.rstrip().split()
        value = [int(val) for val in line]
        if len(value) == 1:
            values.append(value[0])
        else:
            values = value
        sl = sparkline(values, args.width, args.filled, args.min, args.max)
        sys.stdout.write(f"\r{title} {sl} ")
        sys.stdout.flush()
    sys.stdout.write("\n")
