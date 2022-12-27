from __future__ import annotations

import asyncio
import atexit
import math
import random
import shutil
from abc import ABC
from collections import deque
from itertools import pairwise

from astream.event_like import Pulse
from astream.on_time import OnTime
from pymunk import Vec2d

from brailliant.canvas import Canvas
import pymunk

import sys

from examples.android_sensors import get_sensor_output
from examples.async_chars import async_getch

err = deque(maxlen=20)

w, h = shutil.get_terminal_size()

UI_W = 10
UI_W_PADDING = 3
CANVAS_W, CANVAS_H = w * 2 - UI_W - UI_W_PADDING, h

# SIM_SCALE = 0.5
SIM_SCALE = 1
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

    # left_wall = pymunk.Segment(space.static_body, (0, 0), (0, CANVAS_H), 1)
    # top_wall = pymunk.Segment(space.static_body, (0, 0), (CANVAS_W, 0), 1)
    # bottom_wall = pymunk.Segment(
    #     space.static_body,
    #     (0, CANVAS_H),
    #     (CANVAS_W, CANVAS_H),
    #     1,
    # )
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
    MAX_G = 499
    gravy = Vec2d(0, -98.1)
    space.gravity = gravy
    time_step_pulse = Pulse()
    time_step_pulse_back = Pulse()

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

            elif ch == b"x":
                time_step_pulse.fire()
            elif ch == b"z":
                time_step_pulse_back.fire()

    loop = asyncio.get_event_loop()
    t = loop.time()
    time_step = 0.01
    dt = time_step

    def draw_light(copy: Canvas) -> None:
        def raycast(
            light_start: Vec2d,
            light_end: Vec2d,
            light_length: float,
            ignored_shapes: list[pymunk.Shape] | None = None,
        ) -> list[tuple[Vec2d, Vec2d]]:
            """Return the point where the light ray hits the wall."""
            if ignored_shapes is None:
                ignored_shapes = []

            # light_end = light_start + Vec2d(light_length, 0).rotated_degrees(light_angle)
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
            if light_length > 1:
                yield from raycast(
                    next_start,
                    next_end,
                    light_length,
                    ignored_shapes=[col_shape],
                )
            return
            if not seg_query:
                yield (light_start, light_end)
            else:
                next_point = light_end = seg_query.point - seg_query.normal
                yield (light_start, light_end)

                consumed_light_length = light_start.get_distance(next_point)
                remaining_light_length = light_length - consumed_light_length

                if remaining_light_length > 1 and consumed_light_length > 0.1:
                    yield from raycast(
                        seg_query.point,
                        seg_query.normal.angle_degrees,
                        remaining_light_length,
                    )

        light_start = Vec2d(2, CANVAS_H / 2)
        light_end = Vec2d(CANVAS_W - 2, CANVAS_H / 2)
        # rays = raycast(light_start, 0, light_start.get_distance(light_end))
        rays = raycast(light_start, light_end, CANVAS_W * 3)
        # print(rays)
        # exit()
        for ray_start, ray_end in rays:
            try:
                copy.draw_line(*map(int, (ray_start.x, ray_start.y, ray_end.x, ray_end.y)))
            except ValueError:
                pass
        return

        # if seg_query is None:
        #     return light_end

        light_start = Vec2d(2, CANVAS_H / 2)
        light_angle = 20
        light_length = CANVAS_W - 2
        raycast(light_start, light_angle, light_length)
        return
        light_end = light_start + Vec2d(light_length, 0).rotated_degrees(light_angle)
        # light_end = Vec2d(CANVAS_W - CANVAS_W / 3, CANVAS_H / 2)
        seg_query = space.segment_query_first(
            (light_start.x, light_start.y),
            (light_end.x, light_end.y),
            0,
            pymunk.ShapeFilter(),
        )
        if seg_query is not None:

            # light_end = Vec2d(seg_query.point.x, light_end.y)
            light_end = seg_query.point
            # print("\x1b[1;31m", end="", flush=True)
            # Escape sequence to save cursor position: \x1b[s
            # print(f"\033[s\x1b[{math.ceil(CANVAS_H/4)+15};2Hhit   ", end="\033[u", flush=True)
            # Position cursor at
            # sys.stderr.write(repr(seg_query))
        # else:
        #     print(f"\033[s\x1b[{math.ceil(CANVAS_H/4)+15};2Hno hit", end="\033[u", flush=True)
        # print(f"\x1b[{math.ceil(CANVAS_H/4)+5};2H", end="", flush=True)
        # print("\x1b[1;32m", end="", flush=True)
        # Changes color to green

        copy.draw_line(*map(int, (light_start.x, light_start.y, light_end.x, light_end.y)))
        # start_point = (0, CANVAS_H // 2)
        # direction = Vec2d(1, 0)
        # canvas.draw_line(
        #     (int(start_point[0]), int(start_point[1])),
        #     (int(start_point[0] + direction.x * 100), int(start_point[1] + direction.y * 100)),
        # )

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
        draw_light(copy)

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
        space.damping = 0.98
        asyncio.create_task(gravity_from_sensors())
    asyncio.create_task(process_inputs())

    # physics_updater.run_periodically(update_state)

    async def physics_updater() -> None:
        physics_timer = OnTime(1 / RATE)

        async def _update_time():
            nonlocal t, dt, gravy
            while True:
                await physics_timer
                prev_t = t
                t = loop.time()
                dt = t - prev_t
                if time_on:
                    space.step(dt)

        async def _update_time_step_fwd():
            nonlocal time_step
            while True:
                await time_step_pulse
                space.step(time_step)

        async def _update_time_step_bwd():
            nonlocal time_step
            while True:
                await time_step_pulse_back
                space.step(-time_step)

        await asyncio.gather(_update_time(), _update_time_step_fwd(), _update_time_step_bwd())

    asyncio.create_task(physics_updater())

    drawer = OnTime(1 / RATE)
    drawer.run_periodically(draw)

    while True:
        await asyncio.sleep(10)


if __name__ == "__main__":
    mode = "android" if len(sys.argv) > 1 and sys.argv[1] == "--android" else "pc"
    RATE = int(sys.argv[2]) if len(sys.argv) > 2 else 60  # 120 Hz looks great on my monitor :)

    asyncio.run(show_balls())
