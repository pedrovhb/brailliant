import asyncio
import math
import shutil
from pathlib import Path
from typing import AsyncIterator

import PIL
from PIL import ImageFilter, ImageEnhance
from PIL.Image import Image, Dither

from brailliant import Canvas, BRAILLE_ROWS, BRAILLE_COLS

import sys


def scroll_up(lines: int) -> None:
    """Scroll up the terminal by the given number of lines."""
    for i in range(lines):
        sys.stdout.buffer.write(b"\033M")
        sys.stdout.flush()


def scroll_down(lines: int) -> None:
    """Scroll down the terminal by the given number of lines."""
    for i in range(lines):
        sys.stdout.buffer.write(b"\033D")
        sys.stdout.flush()


async def extract_frames_from_video(
    video_file: str | Path,
    fps: float,
    width: int = None,
    height: int = None,
    pil_images: bool = True,
) -> AsyncIterator[Image] | AsyncIterator[bytes]:
    """Extract frames from a video file.

    Extracts frames from a video by wrapping ffmpeg in an asyncio subprocess. The
    frames are decoded as raw RGB data and then converted to a PIL Image.
    Optionally rescales or resizes the video to specific dimensions via an ffmpeg filter.

    Args:
        video_file: The file path to the video.
        fps: The number of frames per second to extract.
        width: The desired width of the video after rescaling. Defaults to None.
        height: The desired height of the video after rescaling. Defaults to None.
        pil_images: Whether to return PIL Images or raw bytes. Defaults to True.

    Returns:
        An async iterator of PIL images.
    """
    probe = await asyncio.create_subprocess_exec(
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "default=noprint_wrappers=1",
        video_file,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Get the video dimensions
    stdout, stderr = await probe.communicate()
    dimensions = stdout.strip().decode("utf-8").split("\n")
    video_width = int(dimensions[0].split("=")[1])
    video_height = int(dimensions[1].split("=")[1])

    # Use the specified dimensions if provided, otherwise use the original dimensions
    if width and height:
        dimensions = str(width) + ":" + str(height)
    else:
        dimensions = str(video_width) + ":" + str(video_height)

    # Calculate the number of bytes per frame
    bytes_per_frame = 3 * width * height

    vf = f"fps={fps},scale={dimensions}" if fps else f"scale={dimensions}"

    # Adjust gamma to make the image brighter
    vf += ",eq=gamma=1.5"

    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-i",
        video_file,
        "-vf",
        vf,
        "-pix_fmt",
        "rgb24",
        "-f",
        "rawvideo",
        "-",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    buf = bytearray()
    while True:
        chunk = await process.stdout.read(bytes_per_frame)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) >= bytes_per_frame:
            bs = bytes(buf[:bytes_per_frame])
            buf = buf[bytes_per_frame:]
            if pil_images:
                yield PIL.Image.frombytes("RGB", (width, height), bs)
            else:
                yield bs

    await process.wait()


def image_to_braille(
    image: Image,
    size: tuple[int, int],
    keep_ratio: bool = True,
    color: bool = False,
) -> str:
    if keep_ratio:
        # PIL.Image.thumbnail() will resize the image to fit within the given dimensions
        # while maintaining the aspect ratio. It will also modify the image in place, so
        # we need to make a copy first.
        image = image.copy()
        image.thumbnail(size)
    else:
        # PIL.Image.resize() will resize the image to the given dimensions, ignoring the
        # aspect ratio. It will create a new image, so we don't need to make a copy.
        image = image.resize(size)

    if color:
        # return _canvas_image_color_with_bg(image)
        return _canvas_image_color_bg(image)
    else:
        return _canvas_image_monochrome(image)


def _canvas_image_monochrome(image: Image) -> str:
    """Draw an image as monochrome to a canvas and return the result as a string."""
    image_dithered = image.filter(ImageFilter.EDGE_ENHANCE_MORE)
    image_dithered = image_dithered.convert("1", dither=Dither.FLOYDSTEINBERG)
    canvas = Canvas(image_dithered.width, image_dithered.height)
    canvas.draw_image(image_dithered)

    return canvas.get_str()


def _canvas_image_color_with_bg(image: Image) -> str:
    """Draw an image as color to a canvas and return the result as a string."""
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
        # Reset style and add a newline
        chars.append("\033[0m\n")

    return "".join(chars)


def _canvas_image_color_no_bg(image: Image) -> str:
    """Draw an image as color to a canvas and return the result as a string."""

    image_color = image.reduce((BRAILLE_COLS, BRAILLE_ROWS))
    image = image.filter(ImageFilter.EDGE_ENHANCE_MORE)
    cell_colors = list(image_color.getdata())

    canvas = Canvas(image.width, image.height)
    canvas.draw_image(image)
    result_text = canvas.get_str()

    chars = []
    color_lines = [
        cell_colors[i : (i + math.ceil(image.width / BRAILLE_COLS))]
        for i in range(0, len(cell_colors), math.ceil(image.width / BRAILLE_COLS))
    ]
    for line, color_line in zip(result_text.splitlines(keepends=False), color_lines):
        for ch, color in zip(line, color_line):
            r, g, b = color
            code = f"38;2;{r};{g};{b}"
            chars.append(f"\033[{code}m{ch}")
        # Reset style and add a newline
        chars.append("\033[0m\n")

    return "".join(chars)


def _canvas_image_color_bg(image: Image) -> str:
    """Draw an image as color to a canvas and return the result as a string."""

    image_color = image.reduce((BRAILLE_COLS, BRAILLE_ROWS))
    image = image.filter(ImageFilter.EDGE_ENHANCE_MORE)
    # Lighten the image
    cell_colors = list(image_color.getdata())

    canvas = Canvas(image.width, image.height)
    canvas.draw_image(image)
    result_text = canvas.get_str()

    chars = []
    color_lines = [
        cell_colors[i : (i + math.ceil(image.width / BRAILLE_COLS))]
        for i in range(0, len(cell_colors), math.ceil(image.width / BRAILLE_COLS))
    ]
    for line, color_line in zip(result_text.splitlines(keepends=False), color_lines):
        for ch, color in zip(line, color_line):
            r, g, b = color

            # Desaturated and darkened color for bg
            r_bg = int(r * 0.3)
            g_bg = int(g * 0.3)
            b_bg = int(b * 0.3)
            code_bg = f"48;2;{r_bg};{g_bg};{b_bg}"
            code = f"38;2;{r};{g};{b}"
            chars.append(f"\033[{code};{code_bg}m{ch}")
        # Reset style and add a newline
        chars.append("\033[0m\n")

    return "".join(chars)
