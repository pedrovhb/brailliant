from __future__ import annotations

import asyncio
import atexit
import math
import random
from abc import ABC
from collections import deque
from itertools import pairwise

from astream.on_time import OnTime
from pymunk import Vec2d

from brailliant.canvas import Canvas
import pymunk

import sys

from examples.android_sensors import get_sensor_output
from examples.async_chars import async_getch

err = deque(maxlen=20)

CANVAS_W, CANVAS_H = 150, 75

SIM_SCALE = 0.5
SHAPE_ELASTICITY = 0.97


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

        x, y = x * SIM_SCALE, y * SIM_SCALE
        vx, vy = vx * SIM_SCALE, vy * SIM_SCALE
        radius *= SIM_SCALE

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
            (int(self.body.position.x / SIM_SCALE), int(self.body.position.y / SIM_SCALE)),
            int(self.shape.radius / SIM_SCALE),
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
        x, y = x * SIM_SCALE, y * SIM_SCALE
        vx, vy = vx * SIM_SCALE, vy * SIM_SCALE
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
                line = tuple(int(x / SIM_SCALE) for x in v0w), tuple(
                    int(x / SIM_SCALE) for x in v1w
                )
                canvas = canvas.draw_line(*line)
            line = tuple(int(x / SIM_SCALE) for x in v1w), tuple(
                int(x / SIM_SCALE) for x in first_vertex
            )
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
        x, y = x * SIM_SCALE, y * SIM_SCALE
        vx, vy = vx * SIM_SCALE, vy * SIM_SCALE
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
                line = tuple(int(x / SIM_SCALE) for x in v0w), tuple(
                    int(x / SIM_SCALE) for x in v1w
                )
                canvas = canvas.draw_line(*line)
            line = tuple(int(x / SIM_SCALE) for x in v1w), tuple(
                int(x / SIM_SCALE) for x in first_vertex
            )
            return canvas.draw_line(*line)


def get_space():
    """Create a Pymunk space with the default gravity and collision handler."""

    # Initialize Pymunk
    space = pymunk.Space()
    space.damping = 0.999

    # Set up the walls as Pymunk segments
    left_wall = pymunk.Segment(space.static_body, (0, 0), (0, CANVAS_H * SIM_SCALE), 1)
    right_wall = pymunk.Segment(
        space.static_body,
        (CANVAS_W * SIM_SCALE, 0),
        (CANVAS_W * SIM_SCALE, CANVAS_H * SIM_SCALE),
        1,
    )
    top_wall = pymunk.Segment(space.static_body, (0, 0), (CANVAS_W * SIM_SCALE, 0), 1)
    bottom_wall = pymunk.Segment(
        space.static_body,
        (0, CANVAS_H * SIM_SCALE),
        (CANVAS_W * SIM_SCALE, CANVAS_H * SIM_SCALE),
        1,
    )
    left_wall.elasticity = 1.0  # Set the elasticity (bounciness) of the walls
    right_wall.elasticity = 1.0
    top_wall.elasticity = 1.0
    bottom_wall.elasticity = 1.0
    space.add(left_wall, right_wall, top_wall, bottom_wall)  # Add the walls to the Pymunk space

    mid_wall = pymunk.Segment(
        space.static_body,
        (round(CANVAS_W * SIM_SCALE / 2), 0),
        (round(CANVAS_W * SIM_SCALE / 2), round(CANVAS_H * SIM_SCALE / 4)),
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


async def show_balls() -> None:
    """Create the canvas and show our balls."""

    initialization = [
        "\x1b[?25l",  # Hide the cursor
        "\x1b[2J",  # Clear the screen
        "\x1b[H",  # Move the cursor to the top left
    ]
    print("".join(initialization), end="", flush=True)

    # Show the cursor on exit
    atexit.register(print, "\x1b[?25h")

    UI_W = 25
    UI_W_PADDING = 5
    canvas = Canvas(CANVAS_W + UI_W + UI_W_PADDING * 2, CANVAS_H)
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
    MAX_G = 499
    gravy = Vec2d(0, -98.1)
    space.gravity = gravy

    async def process_inputs() -> None:
        nonlocal time_on, gravy_on, gravy

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

    async def update_state() -> None:
        """Update the state of the simulation once."""
        nonlocal t, dt, gravy
        prev_t = t
        t = loop.time()
        dt = t - prev_t

        if time_on:
            space.step(dt)

    async def draw():
        """Draw the current state of the simulation."""
        copy = canvas.copy()

        for o in objs:
            copy = o.draw(copy)

        copy.draw_arrow(
            (
                CANVAS_W + UI_W // 2 + UI_W_PADDING,
                CANVAS_H // 2,
            ),
            space.gravity.angle_degrees,
            int(5 * space.gravity.length / MAX_G * UI_W // 2),
            # 6,
        ).draw_circle(
            (CANVAS_W + UI_W // 2 + UI_W_PADDING, CANVAS_H // 2),
            UI_W // 2 + UI_W_PADDING // 2,
        )

        s = copy.get_str_control_chars()
        all_errs = "\033[K\n".join(err)
        fps = 1 / dt
        print(
            s + f"\x1b[{math.ceil(CANVAS_H/4)+1};2H"
            f"\n  g - toggle gravity\t\t\t\tt: toggle time\n"
            f"  up/down arrows: change gravity\t\tleft/right arrows: rotate gravity\n\n"
            f"  gravity: {space.gravity.x:.3f}, {space.gravity.y:.3f}\n"
            f"  fps: {fps:05.1f} \n"
            f"\n{all_errs}\x1b[0;0H",
            end="",
            flush=True,
        )

    async def gravity_from_sensors() -> None:
        while True:
            async for x, y, z in get_sensor_output():
                space.gravity = Vec2d(x, y) * -20
                if space.gravity.length > MAX_G:
                    space.gravity = space.gravity.normalized() * MAX_G

    if mode == "android":
        asyncio.create_task(gravity_from_sensors())
    asyncio.create_task(process_inputs())

    physics_updater = OnTime(1 / RATE)
    physics_updater.run_periodically(update_state)

    drawer = OnTime(1 / RATE)
    drawer.run_periodically(draw)

    while True:
        await asyncio.sleep(10)


if __name__ == "__main__":
    mode = "android" if len(sys.argv) > 1 and sys.argv[1] == "--android" else "pc"
    RATE = int(sys.argv[2]) if len(sys.argv) > 2 else 60  # 120 Hz looks great on my monitor :)

    asyncio.run(show_balls())
