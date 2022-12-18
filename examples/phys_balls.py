from __future__ import annotations
import atexit
import math
import time
from brailliant.canvas import Canvas
import pymunk

CANVAS_W, CANVAS_H = 60, 45

W_SIM_SIZE = 1 * 30
W_SIM_SCALE = CANVAS_W / W_SIM_SIZE
H_SIM_SIZE = 1 * 30
H_SIM_SCALE = CANVAS_H / H_SIM_SIZE


class Ball:
    def __init__(
        self,
        space: pymunk.Space,
        x: float,
        y: float,
        vx: float,
        vy: float,
        radius: float,
        mass: float | None = None,
    ) -> None:

        x, y = x * W_SIM_SCALE, y * H_SIM_SCALE
        vx, vy = vx * W_SIM_SCALE, vy * H_SIM_SCALE
        radius *= W_SIM_SCALE

        if mass is None:
            mass = math.pi * radius**2

        self.body = pymunk.Body(
            mass=mass,
            moment=pymunk.moment_for_circle(mass, 0, radius),
        )
        self.body.position = x, y
        self.body.velocity = vx, vy
        self.shape = pymunk.Circle(self.body, radius)
        self.shape.elasticity = 1.0
        space.add(self.body, self.shape)

    def draw(self, canvas: Canvas) -> None:
        # Draw the ball at its current position in the Pymunk space
        canvas.draw_circle(
            (int(self.body.position.x / W_SIM_SCALE), int(self.body.position.y / H_SIM_SCALE)),
            int(self.shape.radius / W_SIM_SCALE),
            angle_step=1.5,
        )
import math
import pymunk

class Triangle:
    def __init__(
        self,
        space: pymunk.Space,
        x: float,
        y: float,
        vx: float,
        vy: float,
        base: float,
        height: float,
        mass: float | None = None,
    ) -> None:
        # Convert input values to Pymunk scale
        x, y = x * W_SIM_SCALE, y * H_SIM_SCALE
        vx, vy = vx * W_SIM_SCALE, vy * H_SIM_SCALE
        base *= W_SIM_SCALE
        height *= H_SIM_SCALE

        # Calculate mass if not provided
        if mass is None:
            mass = 0.5 * base * height

        # Create the body and shape for the triangle
        self.body = pymunk.Body(mass=mass)
        self.body.position = x, y
        self.body.velocity = vx, vy
        self.shape = pymunk.Poly(self.body, [(0, 0), (base, 0), (base/2, height)])
        self.shape.elasticity = 1.0

        # Add the body and shape to the space
        space.add(self.body, self.shape)

    def draw(self, canvas: Canvas) -> None:
        # Convert the Pymunk coordinates to canvas coordinates
        points = [(int(x / W_SIM_SCALE), int(y / H_SIM_SCALE)) for x, y in self.shape.get_vertices()]
        canvas.draw_rectangle(points, angle_step=1.5)

class Rectangle:
    def __init__(
        self,
        space: pymunk.Space,
        x: float,
        y: float,
        vx: float,
        vy: float,
        width: float,
        height: float,
        mass: float | None = None,
    ) -> None:
        # Convert input values to Pymunk scale
        x, y = x * W_SIM_SCALE, y * H_SIM_SCALE
        vx, vy = vx * W_SIM_SCALE, vy * H_SIM_SCALE
        width *= W_SIM_SCALE
        height *= H_SIM_SCALE

        # Calculate mass if not provided
        if mass is None:
            mass = width * height

        # Create the body and shape for the rectangle
        self.body = pymunk.Body(mass=mass)
        self.body.position = x, y
        self.body.velocity = vx, vy
        self.shape = pymunk.Poly(self.body, [(0, 0), (width, 0), (width, height), (0, height)])
        self.shape.elasticity = 1.0

        # Add the body and shape to the space
        space.add(self.body, self.shape)

    def draw(self


def show_balls():

    initialization = [
        "\x1b[?25l",  # Hide the cursor
        "\x1b[2J",  # Clear the screen
        "\x1b[H",  # Move the cursor to the top left
    ]
    print("".join(initialization), end="", flush=True)

    # Show the cursor on exit
    atexit.register(print, "\x1b[?25h")

    canvas = Canvas(CANVAS_W, CANVAS_H)
    canvas.draw_rectangle((0, 0), (CANVAS_W - 1, CANVAS_H - 1))

    # Initialize Pymunk
    space = pymunk.Space()
    space.gravity = 0, -98.1  # Set the gravity to 0 to disable it

    # Set up the walls as Pymunk segments
    left_wall = pymunk.Segment(space.static_body, (0, 0), (0, CANVAS_H * H_SIM_SCALE), 1)
    right_wall = pymunk.Segment(
        space.static_body,
        (CANVAS_W * W_SIM_SCALE, 0),
        (CANVAS_W * W_SIM_SCALE, CANVAS_H * H_SIM_SCALE),
        1,
    )
    top_wall = pymunk.Segment(space.static_body, (0, 0), (CANVAS_W * W_SIM_SCALE, 0), 1)
    bottom_wall = pymunk.Segment(
        space.static_body,
        (0, CANVAS_H * H_SIM_SCALE),
        (CANVAS_W * W_SIM_SCALE, CANVAS_H * H_SIM_SCALE),
        1,
    )
    left_wall.elasticity = 1.0  # Set the elasticity (bounciness) of the walls
    right_wall.elasticity = 1.0
    top_wall.elasticity = 1.0
    bottom_wall.elasticity = 1.0
    space.add(left_wall, right_wall, top_wall, bottom_wall)  # Add the walls to the Pymunk space

    # Create the objs and add them to the Pymunk space
    objs = [
        Ball(
            space,
            x=CANVAS_W / 2,
            y=CANVAS_H / 2,
            vx=0,  # 5,
            vy=0,  # 5,
            radius=5,
            mass=2,
        ),
        Ball(
            space,
            x=CANVAS_W * 2 / 3,
            y=CANVAS_H * 1 / 3,
            vx=0,  # -10,
            vy=0,  # 14,
            radius=7,
            mass=10,
        ),
    ]
    prev_t = t = time.time()
    # Set up the canvas
    # canvas = Canvas(CANVAS_W, CANVAS_H)
    time_step = 0.01

    # Main loop
    while True:
        time.sleep(time_step)
        prev_t = t
        t = time.time()
        dt = t - prev_t
        space.step(dt)
        fps = 1 / dt
        # Clear the canvas
        copy = canvas.copy()

        # Update the balls' positions and bounce them off walls and each other
        for ball in objs:
            ball.draw(copy)

        # Step the Pymunk space

        # Render the canvas and sleep
        s = copy.get_str_control_chars()
        print(s + f"\x1b[16;0H fps: {fps:.1f}   \x1b[0;0H")


if __name__ == "__main__":
    show_balls()
