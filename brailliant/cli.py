import argparse
import asyncio
import math
import mimetypes
import shutil
import signal
import sys
import textwrap
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

from asynkets import PeriodicPulse, async_getch

from brailliant import sparkline, Canvas
from brailliant.base import BRAILLE_COLS, BRAILLE_ROWS
from brailliant.cli_utils import (
    create_ffmpeg_process,
    extract_frames_from_video,
    image_to_braille,
    InvalidVideoError,
    setup_terminal,
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
        type=str,
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
        "-nc",
        "-bw",
        "--no-colour",
        "--black-and-white",
        "--bw",
        action="store_false",
        dest="color",
        help="Display in black and white (equivalent to --no-color)",
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
    force_media_type.add_argument(
        "--font",
        type=Path,
        default=None,
        help="Show text using a provided font",
    )

    # todo - better handle providing size when using font

    args = parser.parse_args()

    if args.video:
        media_type = "video"
    elif args.image:
        media_type = "image"
    elif args.font:
        media_type = "font"
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
    args.input = Path(args.input) if media_type != "font" else args.input

    term_size = shutil.get_terminal_size()
    size = args.size if args.size else (term_size[0] * BRAILLE_COLS, term_size[1] * BRAILLE_ROWS)

    if media_type == "image":
        display_image(
            file=args.input,
            size=size,
            color=use_color,
            verbose=args.verbose,
            keep_ratio=args.keep_ratio,
            invert=args.invert,
        )
    elif media_type == "video":
        if not shutil.which("ffmpeg"):
            print("Video display requires ffmpeg and ffprobe to be installed and on the PATH.")
            sys.exit(1)

        coro = display_video(
            file=args.input,
            size=size,
            color=use_color,
            verbose=args.verbose,
            keep_ratio=args.keep_ratio,
            fps=args.fps,
            invert=args.invert,
        )
        try:
            asyncio.run(coro)
        except InvalidVideoError:
            print(f"Unable to determine format for file '{args.input}'.", file=sys.stderr)
            sys.exit(1)
    elif media_type == "font":
        display_font_text(
            text=args.input,
            font_path=args.font,
            width=size[0],
            invert=args.invert,
        )
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

    result_text = image_to_braille(
        image=image,
        resize=size,
        keep_ratio=keep_ratio,
        color=color,
        invert=invert,
    )
    height = result_text.count("\n")
    setup_terminal(height + 1)
    print(result_text, end="")


def display_font_text(
    text: str,
    font_path: Path,
    width: int,
    invert: bool,
) -> None:
    """Display text using a font."""
    canvas = Canvas.from_font_text(text=text, font_path=font_path, width=width)
    if invert:
        canvas.invert()
    setup_terminal(math.ceil(canvas.height / BRAILLE_ROWS))
    print(canvas, end="")


async def _show_frames(
    fps: float,
    frame_queue: asyncio.Queue,
    playing_event: asyncio.Event,
) -> None:
    """Show frames from the frame queue to the terminal at the specified framerate."""
    frame_delta = 1 / fps
    current_frame = 0
    periodic_pulse = PeriodicPulse(frame_delta)
    try:
        while True:
            new_frame_fut = await frame_queue.get()

            if new_frame_fut is None:
                break

            new_frame = await new_frame_fut
            current_frame += 1

            await periodic_pulse
            crt_time = current_frame * frame_delta
            h, m, s = crt_time // 3600, crt_time // 60 % 60, crt_time % 60

            if playing_event.is_set():
                # todo - make this prettier with color, braille, and total duration
                # todo (maybe) - handle reversing, make a progress bar, etc.
                state = f"[ PLAYING ⏵   {h:02.0f}:{m:02.0f}:{s:06.3f} ]"
            else:
                state = f"[  PAUSED ⏸   {h:02.0f}:{m:02.0f}:{s:06.3f} ]"
            new_frame: str
            sys.stdout.buffer.write(new_frame.encode().strip() + f"\n{state}\033[u".encode())
            sys.stdout.buffer.flush()
            frame_queue.task_done()

            await playing_event.wait()

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
            return_pil_images=True,
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


async def capture_keys(playing_event: asyncio.Event) -> None:
    """Capture play/pause keys and set the playing event accordingly."""
    try:
        async for ch in async_getch():
            if ch.lower().strip() in (b"", b"p"):
                if playing_event.is_set():
                    playing_event.clear()
                else:
                    playing_event.set()

            elif ch.lower().strip() in (b"q", b"\x03"):
                break

    except asyncio.CancelledError:
        pass


async def display_video(
    file: Path,
    size: tuple[int, int],
    color: bool,
    verbose: bool,
    keep_ratio: bool,
    fps: float,
    invert: bool,
) -> None:

    playing_event = asyncio.Event()
    playing_event.set()
    exit_future = asyncio.Future()

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

    setup_terminal(math.ceil(height / BRAILLE_ROWS) + 1)
    show_frames_task = asyncio.create_task(
        _show_frames(
            fps=fps,
            frame_queue=frame_queue,
            playing_event=playing_event,
        )
    )
    capture_play_pause_keys_task = asyncio.create_task(capture_keys(playing_event=playing_event))
    capture_play_pause_keys_task.add_done_callback(
        lambda _: exit_future.set_result(None) if not exit_future.done() else None
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

    async def cancel_tasks():
        await exit_future
        process_frames_task.cancel()
        show_frames_task.cancel()
        capture_play_pause_keys_task.cancel()

    cancel_tasks_task = asyncio.create_task(cancel_tasks())

    loop.add_signal_handler(
        signal.SIGINT, lambda: exit_future.set_result(None) if not exit_future.done() else None
    )
    await show_frames_task
    if not exit_future.done():
        exit_future.set_result(None)
    await cancel_tasks_task


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
        "-canvas_5",
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
