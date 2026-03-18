from __future__ import annotations

import argparse
import json
from pathlib import Path


MARKER = "<!-- benchmark-report -->"


def load_results(path: Path) -> dict[str, float]:
    payload = json.loads(path.read_text())
    return {
        benchmark["name"]: float(benchmark["stats"]["mean"])
        for benchmark in payload.get("benchmarks", [])
    }


def format_time(seconds: float) -> str:
    if seconds < 1e-6:
        return f"{seconds * 1e9:.0f} ns"
    if seconds < 1e-3:
        return f"{seconds * 1e6:.2f} us"
    if seconds < 1:
        return f"{seconds * 1e3:.2f} ms"
    return f"{seconds:.2f} s"


def render_delta(change_ratio: float) -> tuple[str, str]:
    percent = change_ratio * 100
    if abs(percent) < 2:
        return "about the same", f"{percent:+.1f}%"
    if percent < 0:
        return "faster", f"{percent:+.1f}%"
    return "slower", f"+{percent:.1f}%"


def build_markdown(base: dict[str, float], head: dict[str, float], base_label: str, head_label: str) -> str:
    names = sorted(set(base) | set(head))
    lines = [
        MARKER,
        "## Benchmark Report",
        "",
        f"Comparing `{head_label}` against `{base_label}`.",
        "",
        "| Benchmark | Base | Head | Delta | Status |",
        "| --- | ---: | ---: | ---: | --- |",
    ]

    regressions = 0
    improvements = 0

    for name in names:
        base_time = base.get(name)
        head_time = head.get(name)
        if base_time is None or head_time is None:
            status = "missing"
            delta = "n/a"
            if base_time is None:
                base_display = "n/a"
                head_display = format_time(head_time)
            else:
                base_display = format_time(base_time)
                head_display = "n/a"
        else:
            change_ratio = (head_time - base_time) / base_time if base_time else 0.0
            status, delta = render_delta(change_ratio)
            base_display = format_time(base_time)
            head_display = format_time(head_time)
            if status == "slower":
                regressions += 1
            elif status == "faster":
                improvements += 1

        lines.append(f"| `{name}` | {base_display} | {head_display} | {delta} | {status} |")

    lines.extend(
        [
            "",
            f"- Faster: {improvements}",
            f"- Slower: {regressions}",
            f"- Total benchmarks: {len(names)}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--base-label", type=str, required=True)
    parser.add_argument("--head-label", type=str, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()

    markdown = build_markdown(
        load_results(args.base),
        load_results(args.head),
        base_label=args.base_label,
        head_label=args.head_label,
    )
    args.markdown.write_text(markdown)
    print(markdown)


if __name__ == "__main__":
    main()
