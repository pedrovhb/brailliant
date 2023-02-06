import sys
import shutil
import sys
import textwrap
from functools import partial
from pathlib import Path

from brailliant.base import BRAILLE_COLS, BRAILLE_ROWS
from brailliant.canvas import Canvas

try:
    import PIL

    from PIL.Image import Image, Resampling, Dither, open as image_open
except ImportError:
    raise ImportError(
        "Image display requires the Pillow library. Please install it with 'pip install Pillow'."
    )


def main():
    import argparse

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
            "    $ python braille.py -i input.png\n\n"
            "    # Convert an image to braille and save it to a file:\n"
            "    $ python braille.py -i input.png -o output.txt\n\n"
            "    # Convert an image to a specific size and display it in the terminal:\n"
            "    $ python braille.py -i input.png -s 100 100\n\n"
            "    # Convert an image to braille without dithering and display it in the terminal:\n"
            "    $ python braille.py -i input.png --no-dither\n\n"
            "    # Convert an image to braille and save it to a file, displaying verbose output:\n"
            "    $ python braille.py -i input.png -o output.txt -v\n"
        ),
        add_help=True,
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="The input image file",
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
        "-d",
        "--dither",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Dither the image",
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
    args = parser.parse_args()

    log = partial(print, file=sys.stderr) if args.verbose else lambda message: None

    def green(message: str) -> str:
        return f"\033[32m{message}\033[0m"

    log(f"Loading image {green(args.input)}")
    image = image_open(args.input)

    term_size = shutil.get_terminal_size()
    size = args.size if args.size else (term_size[0] * BRAILLE_COLS, term_size[1] * BRAILLE_ROWS)
    log(f"Converting image to braille with size {'x'.join(map(str, size))}")

    result_text = image_to_braille(
        image=image,
        size=size,
        dither=args.dither,
        keep_ratio=args.keep_ratio,
    )

    if (output_file := args.output) is not None:
        log(f"Writing output to {green(str(output_file))}")
        with output_file.open("w") as f:
            f.write(result_text)
        log(f"Output written to {green(output_file)}")
    else:
        log(f"Writing output to {green('stdout')}")
        sys.stdout.write(result_text)


def image_to_braille(
    image: Image,
    size: tuple[int, int],
    dither: bool = True,
    keep_ratio: bool = True,
) -> str:
    if keep_ratio:
        image = image.copy()  # don't modify the original image
        image.thumbnail(size)
    else:
        image = image.resize(size)

    image = image.convert("1", dither=Dither.FLOYDSTEINBERG if dither else Dither.NONE)

    canvas = Canvas(image.width, image.height)
    canvas.draw_image(image)

    return str(canvas)


if __name__ == "__main__":
    main()
