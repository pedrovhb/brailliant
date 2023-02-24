import asyncio
import atexit
import math
import re
import sys
from asyncio.subprocess import Process
from pathlib import Path
from typing import AsyncIterator

import PIL
from PIL import ImageFilter
from PIL.Image import Dither, Image

from brailliant import BRAILLE_COLS, BRAILLE_ROWS, Canvas


class InvalidVideoError(Exception):
    pass


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


def setup_terminal(lines_buffer: int) -> None:

    # Scroll down enough that the video will be displayed entirely
    scroll_down(lines_buffer)
    scroll_up(lines_buffer)

    # Save the cursor position and hide it
    sys.stdout.write("\033[s\x1b[?25l")
    sys.stdout.flush()

    def teardown() -> None:
        # Restore the cursor position, show it, and scroll down on exit so
        # that transient output doesn't interfere with future usage of the terminal
        sys.stdout.write("\033[u\033[?25h" + "\n" * lines_buffer)

    atexit.register(teardown)


async def create_ffmpeg_process(
    video_file: str | Path,
    fps: float | None = None,
    width: int | None = None,
    height: int | None = None,
    keep_ratio: bool = True,
) -> tuple[Process, int, int, float]:
    """Create an ffmpeg subprocess.

    If width and height are not specified, the video will be decoded at its original
    resolution. If only one of width or height is specified, the video will be decoded
    at the original aspect ratio, but with the specified dimension. If both width and
    height are specified, the video will be decoded at the specified dimensions, or
    the largest possible dimensions that maintain the original aspect ratio if
    keep_ratio is True.

    Args:
        video_file: The path to the video file.
        fps: The desired frames per second. Defaults to None.
        width: The desired width of the video after rescaling. Defaults to None.
        height: The desired height of the video after rescaling. Defaults to None.
        keep_ratio: Whether to keep the aspect ratio when rescaling. Defaults to True.

    Returns:
        A tuple containing the ffmpeg subprocess, the video width, the video height,
        and the video fps.
    """

    vf = []
    if width and height:
        if keep_ratio:
            vf.append(f"scale={width}:{height}:force_original_aspect_ratio=decrease")
        else:
            vf.append(f"scale={width}:{height}")
    elif width:
        vf.append(f"scale={width}:-1")
    elif height:
        vf.append(f"scale=-1:{height}")

    if fps:
        vf.append(f"fps=fps={fps}")

    # Adjust gamma to make the image brighter
    vf.append("eq=gamma=1.5")

    vf_str = ",".join(vf)

    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-i",
        video_file,
        "-vf",
        vf_str,
        "-pix_fmt",
        "rgb24",
        "-f",
        "rawvideo",
        "-",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Parse width, height, and fps from stderr
    # Example lines:
    #   Stream #0:0[0x1](eng): Video: h264 ... 3840x2160, 9279 kb/s, 29.97 fps, 29.97 tbr, ...
    re_info = re.compile(
        r"Stream .*Video:.* (?P<width>\d+)x(?P<height>\d+)\D.* (?P<fps>\d+(?:\.\d+)?) fps"
    )
    is_output = False
    async for line in process.stderr:
        if line.startswith(b"Output"):
            is_output = True

        if is_output and (match := re_info.search(line.decode("utf-8"))):
            width = int(match["width"])
            height = int(match["height"])
            fps = float(match["fps"])
            return process, width, height, fps

    raise InvalidVideoError("Could not parse video info from ffmpeg stderr")


async def extract_frames_from_video(
    process: Process,
    width: int,
    height: int,
    pil_images: bool = True,
) -> AsyncIterator[Image] | AsyncIterator[bytes]:
    """Extract frames from a video file.

    Extracts frames from a video by wrapping ffmpeg in an asyncio subprocess. The
    frames are decoded as raw RGB data and then converted to a PIL Image.
    Optionally rescales or resizes the video to specific dimensions via an ffmpeg filter.

    Args:
        process: The ffmpeg subprocess.
        width: The desired width of the video after rescaling. Defaults to None.
        height: The desired height of the video after rescaling. Defaults to None.
        pil_images: Whether to return PIL Images or raw bytes. Defaults to True.

    Returns:
        An async iterator of PIL images, or raw bytes if pil_images is False.
    """
    bytes_per_frame = 3 * width * height
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
    resize: tuple[int, int] | None = None,
    keep_ratio: bool = True,
    color: bool = False,
    invert: bool = False,
) -> str:
    """Helper function for the CLI tool to display an image in either color or monochrome."""
    image = image.convert("RGB")
    if resize is not None:
        if keep_ratio:
            # PIL.Image.thumbnail() will resize the image to fit within the given dimensions
            # while maintaining the aspect ratio. It will also modify the image in place, so
            # we need to make a copy first.
            image = image.copy()
            image.thumbnail(resize)
        else:
            # PIL.Image.resize() will resize the image to the given dimensions, ignoring the
            # aspect ratio. It will create a new image, so we don't need to make a copy.
            image = image.resize(resize)

    if color:
        # return _canvas_image_color_with_bg(image)
        return _canvas_image_color_bg(image, invert)
    else:
        return _canvas_image_monochrome(image, invert)


def _canvas_image_monochrome(image: Image, invert: bool = False) -> str:
    """Draw an image as monochrome to a canvas and return the result as a string."""
    image_dithered = image.filter(ImageFilter.EDGE_ENHANCE_MORE)
    image_dithered = image_dithered.convert("1", dither=Dither.FLOYDSTEINBERG)
    canvas = Canvas(image_dithered.width, image_dithered.height)
    canvas.draw_image(image_dithered)
    if invert:
        canvas.invert()

    return canvas.get_str()


def _canvas_image_color_with_bg(image: Image, invert: bool = False) -> str:
    """Draw an image as color to a canvas and return the result as a string."""
    image_bg = image.reduce((BRAILLE_COLS, BRAILLE_ROWS))
    canvas = Canvas(image.width, image.height).draw_image(
        image.filter(ImageFilter.EDGE_ENHANCE_MORE).filter(ImageFilter.EDGE_ENHANCE_MORE)
    )
    if invert:
        canvas.invert()

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
    """Draw an image as color to a canvas and return the result as a string.

    Currently unused, because I think the results don't look as good.
    """

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


def _canvas_image_color_bg(image: Image, invert) -> str:
    """Draw an image as color to a canvas and return the result as a string."""

    image_color = image.reduce((BRAILLE_COLS, BRAILLE_ROWS))
    image = image.filter(ImageFilter.EDGE_ENHANCE_MORE)
    # Lighten the image
    cell_colors = list(image_color.getdata())

    canvas = Canvas(image.width, image.height)
    canvas.draw_image(image)
    if invert:
        canvas.invert()
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
