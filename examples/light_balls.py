"""An example usage of brailliant to draw a physics simulation with l4z0rs powered by Pymunk.

Mind that this isn't particularly well-organized or optimized code; it was developed with
the library and things were moving around a lot. It's still really cool, though.
"""


from __future__ import annotations

import argparse
import asyncio
import atexit
import math
import random
import shutil
import signal
import sys
import textwrap
from abc import ABC
from collections import deque
from itertools import chain, pairwise, zip_longest

import pymunk
from asynkets import async_getch, PeriodicPulse

from brailliant import BRAILLE_ROWS
from brailliant.canvas import Canvas
from brailliant.cli_utils import scroll_up, scroll_down, setup_terminal
from examples.android_sensors import get_sensor_output
from pymunk import Vec2d

err = deque(maxlen=20)

w, h = shutil.get_terminal_size()

UI_W = 10
UI_W_PADDING = 3
CANVAS_W, CANVAS_H = w * 2, h - h % 8


SIM_SCALE = 1
SHAPE_ELASTICITY = 0.97
MAX_G = 499


class PhysObj(ABC):
    body: pymunk.Body
    shape: pymunk.Shape


class Ball(PhysObj):
    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        radius: float,
        mass: float | None = None,
    ) -> None:
        x, y = x, y
        vx, vy = vx, vy

        if mass is None:
            mass = math.pi * radius**2

        self.body = pymunk.Body(
            mass=mass,
            moment=pymunk.moment_for_circle(mass, 0, radius),
        )
        self.body.position = x, y
        self.body.velocity = vx, vy
        self.shape = pymunk.Circle(self.body, radius)
        self.shape.elasticity = SHAPE_ELASTICITY

    def draw(self, canvas: Canvas) -> Canvas:
        # Draw the ball at its current position in the Pymunk space
        return canvas.draw_circle(
            (int(self.body.position.x), int(self.body.position.y)),
            int(self.shape.radius),
            angle_step=1.5,
        )


class Rectangle(PhysObj):
    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        width: float,
        height: float,
        mass: float | None = None,
    ) -> None:
        # Convert input values to Pymunk scale
        x, y = x, y
        vx, vy = vx, vy
        width *= SIM_SCALE
        height *= SIM_SCALE

        # Calculate mass if not provided
        if mass is None:
            mass = width * height

        # Create the body and shape for the rectangle
        self.body = pymunk.Body(mass=mass)
        self.body.position = x, y
        self.body.velocity = vx, vy
        self.body.center_of_gravity = (width / 2, height / 2)
        self.body.angular_velocity = 4
        self.shape = pymunk.Poly(self.body, [(0, 0), (width, 0), (width, height), (0, height)])
        self.body.moment = pymunk.moment_for_poly(mass, self.shape.get_vertices())
        self.shape.elasticity = SHAPE_ELASTICITY

    def draw(self, canvas: Canvas) -> Canvas:
        for s in self.body.shapes:
            first_vertex = s.body.local_to_world(s.get_vertices()[0])

            for v0, v1 in pairwise(s.get_vertices()):
                v0w = s.body.local_to_world(v0)
                v1w = s.body.local_to_world(v1)
                line = tuple(int(x) for x in v0w), tuple(int(x) for x in v1w)
                canvas = canvas.draw_line(*line)
            line = tuple(int(x) for x in v1w), tuple(int(x) for x in first_vertex)
            canvas = canvas.draw_line(*line)
        return canvas


class Triangle(PhysObj):
    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        base: float,
        height: float,
        mass: float | None = None,
    ) -> None:
        # Convert input values to Pymunk scale
        x, y = x, y
        vx, vy = vx, vy
        base *= SIM_SCALE
        height *= SIM_SCALE

        # Calculate mass if not provided
        if mass is None:
            mass = 0.5 * base * height

        # Create the body and shape for the triangle
        self.shape = pymunk.Poly(None, [(0, 0), (base, 0), (base / 2, height)])
        self.body = pymunk.Body(
            mass=mass, moment=pymunk.moment_for_poly(mass, self.shape.get_vertices())
        )
        self.body.center_of_gravity = (base / 2, height / 2)
        self.shape.body = self.body
        self.body.position = x, y
        self.body.velocity = vx, vy
        self.shape.elasticity = SHAPE_ELASTICITY

    def draw(self, canvas: Canvas) -> Canvas:
        # Convert the Pymunk coordinates to canvas coordinates
        for s in self.body.shapes:
            first_vertex = s.body.local_to_world(s.get_vertices()[0])

            for v0, v1 in pairwise(s.get_vertices()):
                v0w = s.body.local_to_world(v0)
                v1w = s.body.local_to_world(v1)
                line = tuple(int(x) for x in v0w), tuple(int(x) for x in v1w)
                canvas = canvas.draw_line(*line)
            line = tuple(int(x) for x in v1w), tuple(int(x) for x in first_vertex)
            return canvas.draw_line(*line)


def get_space():
    """Create a Pymunk space with the default gravity and collision handler."""

    # Initialize Pymunk
    space = pymunk.Space()
    space.damping = 0.999

    wall_radius = 30

    # Set up the walls as Pymunk segments
    right_wall = pymunk.Segment(
        space.static_body,
        (CANVAS_W + wall_radius, 0),
        (CANVAS_W + wall_radius, CANVAS_H),
        wall_radius,
    )
    left_wall = pymunk.Segment(
        space.static_body,
        (-wall_radius, 0),
        (-wall_radius, CANVAS_H),
        wall_radius,
    )
    top_wall = pymunk.Segment(
        space.static_body,
        (0, -wall_radius),
        (CANVAS_W, -wall_radius),
        wall_radius,
    )
    bottom_wall = pymunk.Segment(
        space.static_body,
        (0, CANVAS_H + wall_radius),
        (CANVAS_W, CANVAS_H + wall_radius),
        wall_radius,
    )

    left_wall.elasticity = 1.0  # Set the elasticity (bounciness) of the walls
    right_wall.elasticity = 1.0
    top_wall.elasticity = 1.0
    bottom_wall.elasticity = 1.0
    space.add(left_wall, right_wall, top_wall, bottom_wall)  # Add the walls to the Pymunk space

    # Wall in the middle just for show
    mid_wall = pymunk.Segment(
        space.static_body,
        (round(CANVAS_W / 2), 0),
        (round(CANVAS_W / 2), round(CANVAS_H / 4)),
        1,
    )
    mid_wall.elasticity = 1.0
    space.add(mid_wall)

    return space


def get_objs():
    """Create the objects in the simulation."""

    # Create the objs and add them to the Pymunk space
    return [
        Ball(
            x=CANVAS_W / 4,
            y=CANVAS_H / 4,
            vx=random.uniform(-3, 3),
            vy=random.uniform(-3, 3),
            radius=5,
            mass=2,
        ),
        Ball(
            x=CANVAS_W / 4 * 2,
            y=CANVAS_H / 4,
            vx=random.uniform(-3, 3),
            vy=random.uniform(-3, 3),
            radius=11,
            mass=10,
        ),
        Rectangle(
            x=CANVAS_W / 4 * 3,
            y=CANVAS_H / 4 * 2,
            vx=random.uniform(-3, 3),
            vy=random.uniform(-3, 3),
            width=30,
            height=25,
            mass=10,
        ),
        Triangle(
            x=CANVAS_W / 4,
            y=CANVAS_H / 4 * 2,
            vx=random.uniform(-3, 3),
            vy=random.uniform(-3, 3),
            base=20,
            height=22,
            mass=10,
        ),
        Triangle(
            x=CANVAS_W / 4,
            y=CANVAS_H / 4 * 3,
            vx=random.uniform(-3, 3),
            vy=random.uniform(-3, 3),
            base=10,
            height=6,
            mass=3,
        ),
    ]


def raycast(
    space: pymunk.Space,
    light_start: Vec2d,
    light_end: Vec2d,
    light_length: float,
    max_bounces: int | None = None,
    ignored_shapes: list[pymunk.Shape] | None = None,
) -> list[tuple[Vec2d, Vec2d]]:
    """Return the point where the light ray hits the wall."""
    if ignored_shapes is None:
        ignored_shapes = []

    seg_query = space.segment_query(
        (light_start.x, light_start.y),
        (light_end.x, light_end.y),
        0,
        pymunk.ShapeFilter(),
    )
    seg_query_sorted = list(
        sorted(
            [sq for sq in seg_query if sq.shape not in ignored_shapes],
            key=lambda sq: sq.alpha,
        )
    )

    if not seg_query_sorted:
        yield light_start, light_end
        return

    col_query = seg_query_sorted[0]
    light_end = col_query.point
    yield light_start, light_end

    crt_ray = light_end - light_start

    consumed = crt_ray.length
    light_length -= consumed
    if light_length <= 0:
        return
    col_shape = col_query.shape
    normal = col_query.normal
    if isinstance(col_shape, pymunk.Segment):
        normal = normal.rotated_degrees(crt_ray.get_angle_degrees_between(normal) * 2)
    next_start = light_end
    next_end = next_start + normal * light_length
    if light_length > 1 and (max_bounces is None or max_bounces > 0):
        yield from raycast(
            space,
            next_start,
            next_end,
            light_length,
            max_bounces - 1 if max_bounces is not None else None,
            ignored_shapes=[col_shape],
        )


async def show_balls(android_sensors: bool = False) -> None:
    """Create the canvas and show our balls."""

    setup_terminal(CANVAS_H // BRAILLE_ROWS + 8)  # fit the UI and canvas

    canvas = Canvas(CANVAS_W, CANVAS_H)
    canvas.draw_rectangle(0, 0, CANVAS_W - 1, CANVAS_H - 1)
    canvas.draw_line(
        (round(CANVAS_W / 2), 0),
        (round(CANVAS_W / 2), round(CANVAS_H / 4)),
    )

    space = get_space()
    objs = get_objs()
    for obj in objs:
        space.add(obj.body, obj.shape)

    gravy_on = True
    time_on = True
    lasers_bounce_on = False
    lasers_on = False
    gravy = Vec2d(0, -98.1)
    space.gravity = gravy

    async def process_inputs() -> None:
        nonlocal time_on, gravy_on, gravy, lasers_on, lasers_bounce_on

        async for ch in async_getch():
            # Toggle gravity on g
            if ch.lower() == b"g":
                gravy_on = not gravy_on
                if gravy_on:
                    space.gravity = gravy
                else:
                    gravy = space.gravity
                    space.gravity = Vec2d(0, 0)

            # Toggle time on t
            elif ch.lower() == b"t":
                time_on = not time_on

            elif ch.lower() == b"l":
                lasers_on = not lasers_on

            elif ch.lower() == b"b":
                lasers_bounce_on = not lasers_bounce_on

            elif ch == b"\x1b[C":  # Right arrow
                space.gravity = space.gravity.rotated_degrees(6)

            elif ch == b"\x1b[D":  # Left arrow
                space.gravity = space.gravity.rotated_degrees(-6)

            elif ch == b"\x1b[A":  # Up arrow
                space.gravity *= 1.02
                if space.gravity.length > MAX_G:
                    space.gravity = space.gravity.normalized() * MAX_G

            elif ch == b"\x1b[B":  # Down arrow
                space.gravity *= 0.98

    loop = asyncio.get_event_loop()
    t = loop.time()
    time_step = 0.01
    dt = time_step

    def draw_light(copy: Canvas) -> None:
        light_start = Vec2d(2, CANVAS_H / 2)
        rays = chain.from_iterable(
            raycast(
                space,
                light_start,
                light_start + Vec2d(200, 0).rotated_degrees(i / 2),
                CANVAS_W * 0.8,
                max_bounces=8 if lasers_bounce_on else 0,
            )
            for i in range(-30, 31)
        )

        for ray_start, ray_end in rays:
            copy.draw_line(*map(int, (ray_start.x, ray_start.y, ray_end.x, ray_end.y)))

    def get_ui_str():
        fps = 1 / dt
        stats = [
            f"fps: {fps:03.0f}",
            f"gravity: {space.gravity.length:03.2f} ({space.gravity.angle_degrees:03.2f}°)",
            f"gravity on: {gravy_on}",
            f"time on: {time_on}",
            f"laz0rs on: {lasers_on}",
            f"laz0r bounce: {lasers_bounce_on}",
        ]
        keys = [
            "g: toggle gravity",
            "t: toggle time",
            "up/down: gravity strength",
            "left/right: gravity angle",
            "l: toggle laz0rs",
            "b: toggle laz0r bounce",
        ]

        # Draw the UI (stats and keys). It's joined by newlines and the control
        # characters for clearing a line; this is so that the UI is always
        # redrawn (and e.g. updating FPS from 100 to 99 doesn't leave a ghost 1).
        # The UI is displayed in two columns, with the keys on the left and the
        # stats on the right.

        zipped = zip_longest(stats, keys, fillvalue="")

        ui = f"\n\x1b[2K".join(f"\x1b[2K{stat:<30} {key:<30}" for stat, key in zipped)
        ui = textwrap.indent(ui, " " * UI_W_PADDING)
        return ui

    def draw():
        """Draw the current state of the simulation."""
        copy = canvas.copy()

        for o in objs:
            copy = o.draw(copy)
        if lasers_on:
            draw_light(copy)
        ui = get_ui_str()

        s = "".join(
            (
                "\033[u",  # Restore the cursor position
                copy.get_str(),  # Draw the canvas
                "\n\n",  # Move cursor down
                ui,  # Draw the UI
            )
        )

        print(s, end="", flush=True)

    async def android_sensors_update_gravity() -> None:
        async for x, y, z in get_sensor_output():
            space.gravity = Vec2d(x, y) * -20
            if space.gravity.length > MAX_G:
                space.gravity = space.gravity.normalized() * MAX_G

    asyncio.create_task(process_inputs())

    async def update_physics():
        nonlocal t, dt, gravy
        prev_t = t
        t = loop.time()
        dt = t - prev_t
        if time_on:
            space.step(dt)

    drawer = PeriodicPulse(1 / RATE)

    if android_sensors:
        space.damping = 0.98
        drawer.add_pulse_callback(android_sensors_update_gravity)

    drawer.add_pulse_callback(draw)
    drawer.add_pulse_callback(update_physics)

    exit_fut = loop.create_future()

    # SIGTERM vs SIGINT - SIGTERM is sent by the OS when the process is killed
    # (e.g. with `kill`), while SIGINT is sent by the user (e.g. with Ctrl+C).
    asyncio.get_event_loop().add_signal_handler(signal.SIGTERM, exit_fut.set_result, None)
    asyncio.get_event_loop().add_signal_handler(signal.SIGINT, exit_fut.set_result, None)

    await exit_fut
    drawer.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        "Physics simulator",
        description="Simulate physics with pymunk and brailliant.",
    )
    parser.add_argument(
        "--android",
        action="store_true",
        help="Run in android mode (uses Termux API to get sensor data for gravity)",
    )
    parser.add_argument(
        "--rate",
        type=int,
        default=120,
        help="Physics and screen refresh rate",
    )

    args = parser.parse_args()
    RATE = args.rate

    asyncio.run(show_balls(android_sensors=args.android))
