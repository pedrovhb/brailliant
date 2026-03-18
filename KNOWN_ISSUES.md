# Known Issues

## Current Status

- The previously tracked runtime issues in terminal redirection, `Canvas.draw_image()`, `Canvas.draw_arrow()`, rotated rectangles, sparkline iterable handling, sparkline constant-width rendering, `bspark --log-scale`, `bspark --color`, and the experimental sparkbar helper have been fixed on branch `ng`.

## Remaining Issues

- No confirmed runtime issues are currently tracked in the shipped core APIs on branch `ng`.

## Test Coverage Gaps

- Core rendering regressions and experimental sparkbars are now covered in `tests/test_regressions.py` and `tests/test_sparkbars.py`, but video/ffmpeg paths and image/font integration still have lighter automated coverage than the core sparkline and canvas APIs. Refs: `tests/test_brailliant.py`, `tests/test_regressions.py`, `tests/test_sparkbars.py`
