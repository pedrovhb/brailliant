import sys
import shutil
from typing import Literal


from brailliant.base import BRAILLE_COLS, BRAILLE_ROWS, coords_braille_mapping
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

    parser = argparse.ArgumentParser(description="Convert an image to braille.")
    parser.add_argument("-i", "--input", default="input.jpg", help="input image file")
    parser.add_argument("-o", "--output", default="output.png", help="output image file")
    parser.add_argument(
        "-t",
        "--threshold",
        type=int,
        default=128,
        help="threshold for dithering (0-255)",
    )
    # noinspection PyTypeChecker
    parser.add_argument(
        "-f",
        "--fit-terminal",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="fit image to terminal size",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Output logs verbosely",
    )
    args = parser.parse_args()
    print(args)

    term_size = shutil.get_terminal_size()
    print(f"Terminal size: {term_size.columns}x{term_size.lines}")
    # Open the input image
    available_resolution = term_size.columns * 2, term_size.lines * 4
    im = image_open(args.input)
    w, h = available_resolution

    # if args.fit_terminal:

    if args.fit_terminal:
        mw = max(available_resolution[0], w)
        mh = max(available_resolution[1], h)
        ratio = min(mw / w, mh / h)
        w, h = int(w * ratio), int(h * ratio)
        print(f"Resizing to {w}x{h}")
        im = im.resize((w, h), Resampling.LANCZOS)

    canvas = Canvas(w, h)

    sys.stdout.write(str(canvas.draw_image(im)))

if __name__ == "__main__":
    main()


__all__ = ("canvas_from_image", "main", "resize_image")