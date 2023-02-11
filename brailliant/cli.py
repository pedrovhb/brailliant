import argparse
import asyncio
import math
import mimetypes
import shutil
import sys
import textwrap
import time
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path
from textwrap import TextWrapper
from typing import Literal, AsyncIterator

from brailliant import sparkline
from brailliant.base import BRAILLE_COLS, BRAILLE_ROWS, braille_table_str
from brailliant.canvas import Canvas
from brailliant.cli_utils import image_to_braille, extract_frames_from_video, scroll_down, scroll_up

try:
    import PIL
    from PIL import ImageChops, ImageFilter

    from PIL.Image import Dither, Image, open as image_open, Resampling
except ImportError:
    raise ImportError(
        "Image display requires the Pillow library. Please install it with 'pip install Pillow'."
    )


def display_braille_media() -> None:

    parser = argparse.ArgumentParser(
        prog="brailliant",
        description="Display an image or video as braille text.",
        usage=textwrap.dedent(
            """
            Convert an image or video to braille, writing to the terminal or to a file.
            For videos, ffmpeg is required to be installed and on the PATH.
            By default, the image is resized to fit the terminal while maintaining the aspect ratio.
            A specific size can be specified with the --size option.
            
              Examples:
              
                Convert an image to braille and display it in the terminal:
                $ python braille.py input.png
                
                # Convert an image to braille and save it to a file:
                $ python braille.py input.png -o output.txt
                
                # Convert an image to a specific size and display it in the terminal:
                $ python braille.py input.png -s 100 100
                
                # Convert an image to braille without dithering and display it in the terminal:
                $ python braille.py input.png --no-dither
                
                # Convert an image to braille and save it to a file, displaying verbose output:
                $ python braille.py input.png -o output.txt -v
                
                # Display a video in the terminal at 15 frames per second:
                $ python braille.py input.mp4 -f 15
            """.strip()
        ),
        add_help=True,
    )
    parser.add_argument(
        "input",
        type=Path,
        help="The input image or video.",
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
        default=None,
        help="Whether to use color. By default, color is used if the terminal is interactive.",
    )
    parser.add_argument(
        "-r",
        "--fps",
        type=float,
        default=None,
        help="Frames per second to display (for videos only)",
    )

    # Add toggle between forcing video/image
    force_media_type = parser.add_mutually_exclusive_group()
    force_media_type.add_argument(
        "--video",
        action="store_true",
        help="Force the input to be treated as a video",
    )
    force_media_type.add_argument(
        "--image",
        action="store_true",
        help="Force the input to be treated as an image",
    )

    args = parser.parse_args()

    if args.video:
        media_type = "video"
    elif args.image:
        media_type = "image"
    else:
        media_type = mimetypes.guess_type(args.input)[0]
        if media_type and media_type.startswith("image"):
            media_type = "image"
        elif media_type and media_type.startswith("video"):
            media_type = "video"
        else:
            # If the media type is unknown, we'll try to open it as a video. This
            # is so we support e.g. v4l2loopback devices like /dev/video0.
            media_type = "video"

    use_color = args.color if args.color is not None else sys.stdout.isatty()

    if media_type == "image":
        display_image(
            file=args.input,
            size=args.size,
            color=use_color,
            output=args.output,
            verbose=args.verbose,
            keep_ratio=args.keep_ratio,
        )
    elif media_type == "video":
        coro = display_video(
            file=args.input,
            size=args.size,
            color=use_color,
            output=args.output,
            verbose=args.verbose,
            keep_ratio=args.keep_ratio,
            fps=args.fps,
        )
        asyncio.run(coro)
    else:
        print("Unknown media type", file=sys.stderr)
        sys.exit(1)


def display_image(
    file: Path,
    size: tuple[int, int],
    color: bool,
    output: Path | None,
    verbose: bool,
    keep_ratio: bool,
) -> None:
    log = partial(print, file=sys.stderr) if verbose else lambda message: None

    log(f"Loading image {file}")
    image = image_open(file)

    term_size = shutil.get_terminal_size()
    size = size if size else (term_size[0] * BRAILLE_COLS, term_size[1] * BRAILLE_ROWS)
    log(f"Converting image to braille with size {'x'.join(map(str, size))}")

    result_text = image_to_braille(
        image=image,
        size=size,
        keep_ratio=keep_ratio,
        color=color,
    )

    if (output_file := output) is not None:
        log(f"Writing output to {output_file}")
        with output_file.open("w") as f:
            f.write(result_text)
        log(f"Output written to {output_file}")
    else:
        log(f"Writing output to {output_file}")
        print(result_text)


async def display_video(
    file: Path,
    size: tuple[int, int],
    color: bool,
    output: Path,
    verbose: bool,
    keep_ratio: bool,
    fps: float,
) -> None:
    log = partial(print, file=sys.stderr) if verbose else lambda message: None

    log(f"Loading video {file}")

    term_size = shutil.get_terminal_size()
    size = size if size else (term_size[0] * BRAILLE_COLS, term_size[1] * BRAILLE_ROWS)
    log(f"Converting video to braille with size {'x'.join(map(str, size))}")

    # Scroll down enough that the video will be displayed entirely
    vertical_lines = size[1] // BRAILLE_ROWS

    # Scroll down enough that the video will be displayed entirely
    scroll_down(vertical_lines)
    scroll_up(vertical_lines)
    sys.stdout.write("\033[s")

    if output is None:
        output_file = sys.stdout
    else:
        output_file = output.open("w")

    process_pool = ProcessPoolExecutor()

    # Max size here will define the max number of frames queued for processing
    # at any given time. This is to prevent too many frames from being queued
    # and having to wait for future frames to be processed before a previous
    # frame is.
    frame_queue = asyncio.Queue(maxsize=20)

    # todo - get frame interval from video so we don't show frames faster than
    #  the video is playing

    # todo - handle closing the process pool and queue

    async def show_frames():
        while True:
            new_frame_fut = await frame_queue.get()
            new_frame = await new_frame_fut
            if new_frame is None:
                frame_queue.task_done()
                break
            print(new_frame, end="\033[u", flush=True, file=output_file)
            frame_queue.task_done()

            # todo - use asynkets to space frames apart correctly
            await asyncio.sleep(1 / fps if fps else 1 / 30)

    asyncio.create_task(show_frames())

    loop = asyncio.get_running_loop()
    async for frame in extract_frames_from_video(
        video_file=file,
        fps=fps,
        width=size[0],
        height=size[1],
        pil_images=True,
    ):
        fn = partial(
            image_to_braille,
            image=frame,
            size=size,
            keep_ratio=keep_ratio,
            color=color,
        )
        fut = loop.run_in_executor(process_pool, fn)

        # The `await` here prevents the queue from filling up too much -
        # it will only queue up to `maxsize` frames at a time, and the
        # ffmpeg process won't run off producing frames we're not ready
        # to display yet
        await frame_queue.put(fut)

    await frame_queue.join()

    # Scroll down enough that the video will be displayed entirely
    # scroll_down(vertical_lines)
    # scroll_up(vertical_lines)


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
    parser.add_argument(
        "-c",
        "--color",
        type=str,
        choices=["always", "never", "auto"],
        default="auto",
        help="Use color",
    )
    parser.add_argument(
        "-R",
        "--row-size",
        type=int,
        default=8,
        help="Number of bytes per row",
    )
    parser.add_argument(
        "-C",
        "--column-size",
        type=int,
        default=2,
        help="Number of columns per line",
    )

    args = parser.parse_args()
    show_ascii = args.ascii
    bs = args.input.read_bytes()

    use_color = args.color == "always" or (args.color == "auto" and sys.stdout.isatty())

    def hex_to_terminal_color(hex_c: str) -> str:
        hex_c = hex_c.lstrip("#")
        return f"\033[38;2;{int(hex_c[0:2], 16)};{int(hex_c[2:4], 16)};{int(hex_c[4:6], 16)}m"

    def hex_to_terminal_bg_color(hex_c: str) -> str:
        hex_c = hex_c.lstrip("#")
        return f"\033[48;2;{int(hex_c[0:2], 16)};{int(hex_c[2:4], 16)};{int(hex_c[4:6], 16)}m"

    color_fg = hex_to_terminal_color("#c4c8cf")
    color_bg = hex_to_terminal_bg_color("#222237")
    color_padding = hex_to_terminal_bg_color("#323248")
    color_reset = "\033[0m"

    color_bg_0 = hex_to_terminal_bg_color("#7d49aa")
    color_bg_255 = hex_to_terminal_bg_color("#ee455b")
    color_fg_ascii = hex_to_terminal_color("#39ED68")

    def display_character(b: int) -> str:
        """Return a braille string representation of a byte.

        If show_ascii is True, the character will be replaced with the ASCII
        representation of the byte if it is printable.

        Args:
            b: The byte to convert.

        Returns:
            A string representation of the byte.
        """
        ch = chr(b)
        if ch.isascii() and show_ascii and ch.isprintable():
            return ch
        return braille_table_str[b]

    def colorize_character(b: str) -> str:
        """Return a braille string representation of a byte.

        If show_ascii is True, the character will be replaced with the ASCII
        representation of the byte if it is printable.

        Args:
            b: The byte to convert.

        Returns:
            A string representation of the byte.
        """
        if b.isascii():
            return f"{color_bg}{color_fg_ascii}{b}"
        if b == "⣿":
            return f"{color_bg_255}{color_fg}{b}"
        if b == "⠀":
            return f"{color_bg_0}{color_fg}{b}"
        return f"{color_bg}{color_fg}{b}"

    tw = TextWrapper(
        width=args.row_size * args.column_size,
        break_long_words=False,
        break_on_hyphens=False,
        replace_whitespace=False,
    )
    print(tw.fill("hello, world! " * 10))

    # for i, b in enumerate(bs):
    #
    #     ch = display_character(b)
    #     if use_color:
    #         ch = colorize_character(ch)
    #
    #     if i % (args.row_size * args.column_size) == 0:
    #         print(color_reset)
    #     elif i % args.row_size == 0:
    #         print(f"{color_reset}{color_padding}  {color_reset}", end="")
    #
    #     print(ch, end="")


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


if __name__ == "__main__":
    display_braille_media()
