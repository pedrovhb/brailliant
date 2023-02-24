import argparse
import asyncio
import atexit
import mimetypes
import shutil
import signal
import sys
import textwrap
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

from asynkets import PeriodicPulse

from brailliant import sparkline
from brailliant.base import BRAILLE_COLS, BRAILLE_ROWS
from brailliant.cli_utils import (
    create_ffmpeg_process,
    extract_frames_from_video,
    image_to_braille,
    InvalidVideoError,
    scroll_down,
    scroll_up,
)

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
                $ python braille.py input.png > output.txt
                
                # Convert an image to a specific size and display it in the terminal:
                $ python braille.py input.png -s 100 100
                
                # Convert an image to braille and save it to a file, displaying verbose output:
                $ python braille.py input.png -v > output.txt
                
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
        "-i",
        "--invert",
        action="store_true",
        default=False,
        help="Invert the image's colors in black/white mode, or the outlining in color mode.",
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
            verbose=args.verbose,
            keep_ratio=args.keep_ratio,
            invert=args.invert,
        )
    elif media_type == "video":
        if not shutil.which("ffmpeg"):
            print(
                "Video display requires ffmpeg and ffprobe to be installed and on the PATH."
            )
            sys.exit(1)

        coro = display_video(
            file=args.input,
            size=args.size,
            color=use_color,
            verbose=args.verbose,
            keep_ratio=args.keep_ratio,
            fps=args.fps,
            invert=args.invert,
        )
        try:
            asyncio.run(coro)
        except InvalidVideoError:
            print(
                f"Unable to determine format for file '{args.input}'.", file=sys.stderr
            )
            sys.exit(1)
    else:
        print("Unknown media type", file=sys.stderr)
        sys.exit(1)


def display_image(
    file: Path,
    size: tuple[int, int],
    color: bool,
    verbose: bool,
    keep_ratio: bool,
    invert: bool,
) -> None:
    log = partial(print, file=sys.stderr) if verbose else lambda message: None

    log(f"Loading image {file}")
    image = image_open(file)

    term_size = shutil.get_terminal_size()
    size = size if size else (term_size[0] * BRAILLE_COLS, term_size[1] * BRAILLE_ROWS)
    log(f"Converting image to braille with size {'x'.join(map(str, size))}")

    result_text = image_to_braille(
        image=image,
        resize=size,
        keep_ratio=keep_ratio,
        color=color,
        invert=invert,
    )
    print(result_text)


async def _show_frames(fps: float, frame_queue: asyncio.Queue) -> None:
    """Show frames from the frame queue to the terminal at the specified framerate."""
    periodic_pulse = PeriodicPulse(1 / fps)
    try:
        while True:
            new_frame_fut = await frame_queue.get()

            if new_frame_fut is None:
                break

            new_frame = await new_frame_fut

            await periodic_pulse
            sys.stdout.buffer.write(new_frame.encode().strip() + b"\033[u")
            sys.stdout.buffer.flush()
            frame_queue.task_done()

    except asyncio.CancelledError:
        pass
    finally:
        periodic_pulse.close()


async def process_frames(
    proc: asyncio.subprocess.Process,
    width: int,
    height: int,
    color: bool,
    invert: bool,
    frame_queue: asyncio.Queue,
) -> None:
    """Process frames from the ffmpeg process and put them on the frame queue."""

    loop = asyncio.get_running_loop()
    process_pool = ProcessPoolExecutor()

    try:
        async for frame in extract_frames_from_video(
            process=proc,
            width=width,
            height=height,
            pil_images=True,
        ):
            fn = partial(
                image_to_braille,
                invert=invert,
                image=frame,
                color=color,
            )
            fut = loop.run_in_executor(process_pool, fn)

            # The `await` here prevents the queue from filling up too much -
            # it will only queue up to `maxsize` frames at a time, and the
            # ffmpeg process won't run off producing frames we're not ready
            # to display yet
            await frame_queue.put(fut)

        await frame_queue.put(None)
    finally:
        process_pool.shutdown(cancel_futures=True)


async def display_video(
    file: Path,
    size: tuple[int, int],
    color: bool,
    verbose: bool,
    keep_ratio: bool,
    fps: float,
    invert: bool,
) -> None:
    log = partial(print, file=sys.stderr) if verbose else lambda message: None

    log(f"Loading video {file}")

    term_size = shutil.get_terminal_size()
    size = size if size else (term_size[0] * BRAILLE_COLS, term_size[1] * BRAILLE_ROWS)

    # Max size here will define the max number of frames queued for processing
    # at any given time. This is to prevent too many frames from being queued
    # and having to wait for future frames to be processed before a previous
    # frame is.
    frame_queue = asyncio.Queue(maxsize=50)

    loop = asyncio.get_running_loop()

    proc, width, height, fps = await create_ffmpeg_process(
        video_file=file,
        fps=fps,
        width=size[0],
        height=size[1],
        keep_ratio=keep_ratio,
    )

    # Scroll down enough that the video will be displayed entirely
    vertical_lines = height // BRAILLE_ROWS

    # Scroll down enough that the video will be displayed entirely
    scroll_down(vertical_lines)
    scroll_up(vertical_lines)
    sys.stdout.write("\033[s")

    # Scroll down on exit so that transient output doesn't interfere with future usage of
    # the terminal
    atexit.register(sys.stdout.write, "\033[u" + "\n" * (vertical_lines + 1))

    # Hide cursor (but enable at exit)
    sys.stdout.write("\033[?25l")
    atexit.register(sys.stdout.write, "\033[?25h")

    show_frames_task = asyncio.create_task(
        _show_frames(fps=fps, frame_queue=frame_queue)
    )

    log(f"Converting video to braille with size {width}x{height}")

    process_frames_task = asyncio.create_task(
        process_frames(
            proc=proc,
            width=width,
            height=height,
            color=color,
            invert=invert,
            frame_queue=frame_queue,
        )
    )

    def cancel_tasks():
        process_frames_task.cancel()
        show_frames_task.cancel()

    loop.add_signal_handler(signal.SIGINT, cancel_tasks)

    await show_frames_task


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
