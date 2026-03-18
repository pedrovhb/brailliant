from __future__ import annotations

from brailliant import Canvas, DrawMode, TextAlign, sparkline
from brailliant._experimental.sparkbars import get_sparkbar, get_sparkbar_normalized


if __name__ == "__main__":
    print("Sparkline")
    print(sparkline([1, 2, 3, 5, 8, 13, 8, 5, 3, 2, 1], width=8))
    print()

    print("Sparkbar")
    print(get_sparkbar([3, 6, 10, 2], min_width=6))
    print(get_sparkbar_normalized([4, 8, 15, 16], width=8))
    print()

    print("Canvas")
    canvas = Canvas(40, 20)
    canvas.draw_border(margin=1)
    canvas.draw_circle(10, 10, 6, filled=False)
    canvas.draw_rectangle(26, 10, 10, 8, filled=True, mode=DrawMode.ADD)
    canvas.write_text(20, 8, "Hi", alignment=TextAlign.CENTER)
    print(canvas)
