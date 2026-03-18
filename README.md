# ⢀⣀⣠⣊⣉⡉ brailliant ⢉⣑⣄⣀⡀
Bring your data to life with Brailliant: the library for creating beautiful, accessible sparklines and terminal images with Braille Unicode characters.

## Development

- Install dependencies with `uv sync --group dev`.
- Run tests with `uv run pytest tests -q`.
- Run the CLI with `uv run brailliant <input>` or `uv run bspark`.

## Benchmarks

- Baseline benchmarks live in `benchmarks/test_core.py`.
- Run them locally with `uv run pytest benchmarks -q --benchmark-only --benchmark-sort=mean --benchmark-json .benchmarks/latest.json`.
- Compare two saved runs locally with `uv run python scripts/compare_benchmarks.py --base old.json --head new.json --base-label old --head-label new --markdown report.md`.
- GitHub Actions now uploads benchmark artifacts and posts a benchmark comparison comment on pull requests.

## todo

- [ ] Use an optimized algorithm for the main canvas class, possibly using bitstream rather than ints
