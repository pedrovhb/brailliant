from __future__ import annotations

from brailliant import coords_to_braille, sparkline
from brailliant.canvas import Canvas


def test_coords_to_braille(benchmark) -> None:
    benchmark(coords_to_braille, (0, 0), (1, 0), (0, 3), (1, 3))


def test_sparkline(benchmark) -> None:
    data = [((i * 7) % 101) - 20 for i in range(400)]
    benchmark(lambda: sparkline(data, width=120, filled=True, min_val=None, max_val=None))


def test_canvas_draw_circle(benchmark) -> None:
    def run() -> Canvas:
        canvas = Canvas(160, 80)
        canvas.draw_circle(40, 40, 20, filled=False)
        canvas.draw_circle(120, 40, 20, filled=True)
        canvas.draw_grid(8, 8, dotting=2)
        return canvas

    benchmark(run)


def test_canvas_get_str(benchmark) -> None:
    canvas = Canvas(160, 80)
    canvas.draw_circle(40, 40, 20, filled=False)
    canvas.draw_circle(120, 40, 20, filled=True)
    canvas.draw_grid(8, 8, dotting=2)
    benchmark(canvas.get_str)
