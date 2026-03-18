# Known Issues

## Current Status

- The previously tracked runtime issues in terminal redirection, `Canvas.draw_image()`, `Canvas.draw_arrow()`, rotated rectangles, sparkline iterable handling, sparkline constant-width rendering, and `bspark --log-scale` have been fixed on branch `ng`.

## Remaining Issues

- The experimental sparkbar helper is still unfinished and should be treated as unstable. It contains an in-file `todo` and is not covered by tests. Ref: `brailliant/_experimental/sparkbars.py:94`

## Test Coverage Gaps

- Core rendering regressions are now covered in `tests/test_regressions.py`, but video/ffmpeg paths and image/font integration still have lighter automated coverage than the core sparkline and canvas APIs. Refs: `tests/test_brailliant.py`, `tests/test_regressions.py`
