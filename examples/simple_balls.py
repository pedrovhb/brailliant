from __future__ import annotations

import atexit
import time

from brailliant.canvas import Canvas

CANVAS_W, CANVAS_H = 90, 55


class Ball:
    x: float
    y: float
    vx: float
    vy: float
    radius: float

    __slots__ = ("x", "y", "vx", "vy", "radius", "shape")

    def __init__(self, x: float, y: float, vx: float, vy: float, radius: float) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.radius = radius

    def move(self, dt: float) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt

    def bounce(self, width: int, height: int, balls: list[Ball] | None = None) -> None:
        if self.x < self.radius:
            self.x = self.radius
            self.vx = -self.vx
        elif self.x > width - self.radius:
            self.x = width - self.radius
            self.vx = -self.vx
        if self.y < self.radius:
            self.y = self.radius
            self.vy = -self.vy
        elif self.y > height - self.radius:
            self.y = height - self.radius
            self.vy = -self.vy

        if balls is not None:
            for ball in balls:
                if ball is self:
                    continue
                dx = ball.x - self.x
                dy = ball.y - self.y
                d = (dx**2 + dy**2) ** 0.5
                if int(d) <= ball.radius + self.radius:
                    self.vx, ball.vx = ball.vx, self.vx
                    self.vy, ball.vy = ball.vy, self.vy

    def draw(self, canvas: Canvas) -> None:
        canvas.draw_circle(int(self.x), int(self.y), int(self.radius), False, angle_step=1.5)


def show_balls() -> None:
    initialization = [
        "\x1b[?25l",  # Hide the cursor
        "\x1b[2J",  # Clear the screen
        "\x1b[H",  # Move the cursor to the top left
    ]
    print("".join(initialization), end="", flush=True)

    # Show the cursor on exit
    atexit.register(print, "\x1b[?25h")

    balls = [
        Ball(40, 60, 55, -45, 5),
        Ball(10, 40, -10, 14, 7),
        Ball(30, 20, -35, -15, 13),
    ]
    canvas = Canvas(CANVAS_W, CANVAS_H)
    canvas.draw_rectangle(0, 0, CANVAS_W - 1, CANVAS_H - 1)

    t = time.perf_counter()
    prev_t = t
    while True:
        dt = t - prev_t
        prev_t = t
        t = time.perf_counter()
        fps = 1 / (dt or 1)

        copy = canvas.copy()

        for ball in balls:
            ball.move(dt)
            ball.bounce(canvas.width, canvas.height, balls)
            ball.draw(copy)

        s = copy.get_str()

        print(
            s + f"\x1b[16;0H fps: {fps:.1f}                 \x1b[0;0H",
            flush=True,
            end="",
        )


if __name__ == "__main__":
    show_balls()
