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


def resize_image(
    image_path: str,
    width: int,
    height: int,
    keep_ratio: bool = True,
    crop_pixels: tuple[int, int, int, int] | None = None,
    crop_percentage: tuple[float, float, float, float] | None = None,
) -> Image:
    """Resizes an image for drawing on a limited canvas.

    Args:
        image_path: Path to the image file.

        width: Desired width of the resized image.

        height: Desired height of the resized image.

        keep_ratio: Boolean indicating whether to keep the original image ratio. If True,
            the image proportions are kept by leaving blank space. If False, they are distorted to
            fit the desired size.

        crop_pixels: Tuple specifying an area of the image for cropping in pixels. The tuple
            should contain x0, y0, x1, y1 coordinates as they relate to pixels in the original
            image.

        crop_percentage: Tuple specifying an area of the image for cropping in percentage. The
            tuple should contain x0, y0, x1, y1 coordinates as they relate to the original image
            size.

    Returns:
        The resized image.
    """
    image = image_open(image_path).convert("1")

    # If cropping, get the area specified in the original image size
    if crop_pixels is not None:
        x0, y0, x1, y1 = crop_pixels
        image = image.crop((x0, y0, x1, y1))
    elif crop_percentage is not None:
        x0f, y0f, x1f, y1f = crop_percentage
        x0 = int(x0f * image.width)
        y0 = int(y0f * image.height)
        x1 = int(x1f * image.width)
        y1 = int(y1f * image.height)
        image = image.crop((x0, y0, x1, y1))

    # Calculate the new size
    if keep_ratio:
        original_ratio = image.width / image.height
        new_ratio = width / height
        if new_ratio > original_ratio:
            # New width is the limiting factor
            new_height = int(width / original_ratio)
            new_width = width
        else:
            # New height is the limiting factor
            new_width = int(height * original_ratio)
            new_height = height
    else:
        new_width = width
        new_height = height

    # Resize the image
    image = image.resize((new_width, new_height))

    return image


def canvas_from_image(
    raw_bytes: bytes,
    img_width: int,
    img_height: int,
    mode: Literal["add", "clear"] = "add",
) -> Canvas:
    """Sets the canvas to the given image, using raw_bytes as the image data.

    The image data should be in the format of a 1-bit per pixel image, with the first byte being the top-left pixel, and the last byte being the bottom-right pixel. This is the format used by PIL.Image.tobytes(). Thus, to use this function from an image, you should use something like:

    >>> from PIL import Image
    >>> image = Image.open("image.png")
    >>> image = image.convert("1")
    >>> canvas = canvas_from_image(image.tobytes(), image.width, image.height)

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
    row_start, row_end = 0, img_width // BRAILLE_COLS
    col_start, col_end = 0, img_height // BRAILLE_ROWS
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
    delta = 0
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


def main() -> None:
    # Parse the command line arguments -
    #   -i or --input is the input image file
    #   -o or --output is the output image file
    #   -t or --threshold is the threshold for dithering
    #   -s or --size is the size of the output image
    #   -h or --help is the help message
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
