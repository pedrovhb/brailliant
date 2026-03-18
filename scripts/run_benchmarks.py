from __future__ import annotations

import argparse
import importlib
import json
import statistics
import sys
import time
from pathlib import Path


def load_modules(source_root: Path):
    source_root = source_root.resolve()
    sys.path.insert(0, str(source_root))
    for module_name in list(sys.modules):
        if module_name == "brailliant" or module_name.startswith("brailliant."):
            del sys.modules[module_name]

    brailliant = importlib.import_module("brailliant")
    canvas_module = importlib.import_module("brailliant.canvas")
    return brailliant, canvas_module


def measure(fn, *, rounds: int, iterations: int, warmup: int = 2) -> dict[str, float | int]:
    for _ in range(warmup):
        for _ in range(iterations):
            fn()

    samples = []
    for _ in range(rounds):
        start = time.perf_counter()
        for _ in range(iterations):
            fn()
        samples.append((time.perf_counter() - start) / iterations)

    return {
        "min": min(samples),
        "max": max(samples),
        "mean": statistics.mean(samples),
        "median": statistics.median(samples),
        "rounds": rounds,
        "iterations": iterations,
    }


def build_benchmarks(source_root: Path) -> dict[str, object]:
    brailliant, canvas_module = load_modules(source_root)
    coords_to_braille = brailliant.coords_to_braille
    sparkline = brailliant.sparkline
    Canvas = canvas_module.Canvas

    sparkline_data = [((i * 7) % 101) - 20 for i in range(400)]

    def bench_coords_to_braille() -> None:
        coords_to_braille((0, 0), (1, 0), (0, 3), (1, 3))

    def bench_sparkline() -> None:
        sparkline(sparkline_data, width=120, filled=True, min_val=None, max_val=None)

    def bench_canvas_draw_circle() -> None:
        canvas = Canvas(160, 80)
        canvas.draw_circle(40, 40, 20, filled=False)
        canvas.draw_circle(120, 40, 20, filled=True)
        canvas.draw_grid(8, 8, dotting=2)

    canvas_for_str = Canvas(160, 80)
    canvas_for_str.draw_circle(40, 40, 20, filled=False)
    canvas_for_str.draw_circle(120, 40, 20, filled=True)
    canvas_for_str.draw_grid(8, 8, dotting=2)

    def bench_canvas_get_str() -> None:
        canvas_for_str.get_str()

    cases = [
        ("coords_to_braille", bench_coords_to_braille, 12, 200_000),
        ("sparkline", bench_sparkline, 10, 500),
        ("canvas_draw_circle", bench_canvas_draw_circle, 10, 50),
        ("canvas_get_str", bench_canvas_get_str, 10, 50),
    ]

    return {
        "source_root": str(source_root.resolve()),
        "benchmarks": [
            {
                "name": name,
                "stats": measure(fn, rounds=rounds, iterations=iterations),
            }
            for name, fn, rounds, iterations in cases
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = build_benchmarks(args.source_root)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
