# Known Issues

## High

- `brailliant` output redirection is currently broken. The CLI advertises `> output.txt`, but terminal setup still calls `get_terminal_size()` in non-TTY contexts and can raise `OSError` or emit terminal escape codes instead. Refs: `brailliant/cli.py:52`, `brailliant/cli.py:233`, `brailliant/cli.py:247`, `brailliant/cli_utils.py:38`
- `Canvas.draw_image()` always writes `final_img.png` into the current working directory, which creates an unexpected filesystem side effect and can overwrite existing files. Ref: `brailliant/canvas.py:783`
- `Canvas.draw_arrow()` is broken at runtime because it passes coordinate tuples into `_draw_line()`, which expects four integer arguments. Refs: `brailliant/canvas.py:41`, `brailliant/canvas.py:266`, `brailliant/canvas.py:267`, `brailliant/canvas.py:274`, `brailliant/canvas.py:699`

## Medium

- Rotated rectangles are positioned incorrectly because `_draw_rectangle()` rotates absolute coordinates around the origin instead of the requested anchor point. Refs: `brailliant/canvas.py:233`, `brailliant/canvas.py:244`
- `sparkline()` renders constant series with the wrong width by returning one blank character per sample instead of the normal braille cell width. Refs: `brailliant/sparklines.py:151`, `brailliant/sparklines.py:153`
- `bspark --log-scale` is currently ignored because the CLI parses the flag but never forwards it to `sparkline()`. Refs: `brailliant/cli.py:467`, `brailliant/cli.py:494`
- Empty generators are mishandled by the sparkline APIs because the emptiness check happens before non-sequence iterables are materialized; width padding is skipped and an empty string is returned instead. Refs: `brailliant/sparklines.py:42`, `brailliant/sparklines.py:45`, `brailliant/sparklines.py:133`, `brailliant/sparklines.py:136`
- `sparkline_non_normalized()` mutates shared mapping dictionaries via `setdefault()`, which is unnecessary global state mutation in a rendering hot path. Ref: `brailliant/sparklines.py:61`

## Test Coverage Gaps

- The current automated tests cover core braille conversion, sparklines, and a small slice of `Canvas`, but do not cover CLI behavior, ffmpeg/video paths, image/font rendering, rotated rectangles, or arrows. Ref: `tests/test_brailliant.py`
