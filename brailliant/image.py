import shutil
import sys

from brailliant import coords_braille_mapping
from brailliant.canvas import Canvas

try:
    from PIL import Image
except ImportError:
    raise ImportError(
        "Image display requires the Pillow library. Please install it with 'pip install Pillow'."
    )


def resize_image(
    image_path: str,
    width: int,
    height: int,
    keep_ratio: bool = True,
    crop_pixels: tuple[int, int, int, int] = None,
    crop_percentage: tuple[float, float, float, float] = None,
) -> Image:
    """Resizes an image for drawing on a limited canvas.

    Args:
        image_path: Path to the image file.
        width: Desired width of the resized image.
        height: Desired height of the resized image.
        keep_ratio: Boolean indicating whether to keep the original image ratio. If True, the image proportions are kept by leaving blank space. If False, they are distorted to fit the desired size.
        crop_pixels: Tuple specifying an area of the image for cropping in pixels. The tuple should contain x0, y0, x1, y1 coordinates as they relate to pixels in the original image.
        crop_percentage: Tuple specifying an area of the image for cropping in percentage. The tuple should contain x0, y0, x1, y1 coordinates as they relate to the original image size.

    Returns:
        The resized image.
    """
    image = Image.open(image_path)

    # If cropping, get the area specified in the original image size
    if crop_pixels:
        x0, y0, x1, y1 = crop_pixels
        image = image.crop((x0, y0, x1, y1))
    elif crop_percentage:
        x0, y0, x1, y1 = crop_percentage
        x0 = int(x0 * image.width)
        y0 = int(y0 * image.height)
        x1 = int(x1 * image.width)
        y1 = int(y1 * image.height)
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


if __name__ == "__main__":

    # Parse the command line arguments -
    #   -i or --input is the input image file
    #   -o or --output is the output image file
    #   -t or --threshold is the threshold for dithering
    #   -s or --size is the size of the output image
    #   -h or --help is the help message
    import argparse

    parser = argparse.ArgumentParser(description="Convert an image to braille.")
    parser.add_argument("-i", "--input", default="input.jpg", help="input image file")
    parser.add_argument(
        "-o", "--output", default="output.png", help="output image file"
    )
    parser.add_argument(
        "-t",
        "--threshold",
        type=int,
        default=128,
        help="threshold for dithering (0-255)",
    )
    # parser.add_argument("-s", "--size", type=int, default=100, help="size of the output image")
    args = parser.parse_args()

    keep_ratio = True

    term_size = shutil.get_terminal_size()
    print(f"Terminal size: {term_size.columns}x{term_size.lines}")
    # Open the input image
    available_resolution = term_size.columns * 2, term_size.lines * 4
    im = Image.open(args.input)
    max_w, max_h = im.width, im.height
    if keep_ratio:
        h = max(available_resolution[1], max_h)
        w = max(available_resolution[0], max_w)

    # canvas = Canvas(im.width, im.height).with_changes(dither_coords(im), "add")

    canvas = Canvas.from_image(im.tobytes(), im.width, im.height).get_str()
    print(canvas)
