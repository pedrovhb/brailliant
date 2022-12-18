from __future__ import annotations
import atexit
import time
from brailliant.canvas import Canvas
import pymunk

CANVAS_W, CANVAS_H = 60, 45


class Ball:
    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        radius: float,
        space: pymunk.Space,
    ) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.radius = radius
        self.mass = 1  # Set the mass of the ball
        self.moment = pymunk.moment_for_circle(
            self.mass, 0, self.radius
        )  # Calculate the moment of inertia
        self.body = pymunk.Body(
            self.mass, self.moment
        )  # Create a physical body for the ball
        self.body.position = self.x, self.y  # Set the initial position of the body
        self.shape = pymunk.Circle(
            self.body, self.radius
        )  # Create a physical shape for the ball
        self.shape.elasticity = 1.0  # Set the elasticity (bounciness) of the ball
        space.add(self.body, self.shape)  # Add the body and shape to the Pymunk space

    #    def move(self, dt: float) -> None:
    # Update the ball's position based on its velocity
    #       self.body.position += self.vx * dt, self.vy * dt

    def bounce(self, width: int, height: int, balls: list[Ball] | None = None) -> None:

        # Check if the ball has collided with any other balls and bounce them off each other
        if balls is not None:
            for ball in balls:
                if ball is self:
                    continue
                if pymunk.collision.segment_query(
                    self.body.position,
                    ball.body.position,
                    self.shape.radius + ball.shape.radius,
                    space,
                ):
                    self.body.velocity, ball.body.velocity = (
                        ball.body.velocity,
                        self.body.velocity,
                    )

    def draw(self, canvas: Canvas) -> None:
        # Draw the ball at its current position in the Pymunk space
        canvas.draw_circle(
            (int(self.body.position.x), int(self.body.position.y)),
            int(self.radius),
            angle_step=1.5,
        )


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
    canvas.draw_rectangle((1, 1), (CANVAS_W - 1, CANVAS_H - 1))

    # Initialize Pymunk
    space = pymunk.Space()
    space.gravity = 2, 9.8  # Set the gravity to 0 to disable it

    # Set up the walls as Pymunk segments
    left_wall = pymunk.Segment(space.static_body, (0, 0), (0, CANVAS_H), 1)
    right_wall = pymunk.Segment(
        space.static_body, (CANVAS_W, 0), (CANVAS_W, CANVAS_H), 1
    )
    top_wall = pymunk.Segment(space.static_body, (0, 0), (CANVAS_W, 0), 1)
    bottom_wall = pymunk.Segment(
        space.static_body, (0, CANVAS_H), (CANVAS_W, CANVAS_H), 1
    )
    left_wall.elasticity = 1.0  # Set the elasticity (bounciness) of the walls
    right_wall.elasticity = 1.0
    top_wall.elasticity = 1.0
    bottom_wall.elasticity = 1.0
    space.add(
        left_wall, right_wall, top_wall, bottom_wall
    )  # Add the walls to the Pymunk space

    # Create the balls and add them to the Pymunk space
    balls = [
        Ball(CANVAS_W / 2, CANVAS_H / 2, 5, 5, 5, space),
        Ball(10, 40, -10, 14, 7, space),
        # Ball(30, 20, -35, -15, 13, space),
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
        fps = 1 / dt
        # Clear the canvas
        copy = canvas.copy()

        # Update the balls' positions and bounce them off walls and each other
        for ball in balls:
            # ball.move(dt)
            # ball.bounce(CANVAS_W, CANVAS_H, balls)
            ball.draw(copy)

        # Step the Pymunk space
        space.step(dt)

        # Render the canvas and sleep
        s = copy.get_str_control_chars()
        print(s + f"\x1b[16;0H fps: {fps:.1f}   \x1b[0;0H")


if __name__ == "__main__":
    show_balls()
