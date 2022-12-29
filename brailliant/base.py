from typing import Final

BRAILLE_COLS: Final[int] = 2
BRAILLE_ROWS: Final[int] = 4

BRAILLE_RANGE_START: Final[int] = 0x2800

coords_braille_mapping: Final[dict[tuple[int, int], int]] = {
    (0, 3): 1 << 0,  # ⠁
    (0, 2): 1 << 1,  # ⠂
    (0, 1): 1 << 2,  # ⠄
    (0, 0): 1 << 6,  # ⡀
    (1, 3): 1 << 3,  # ⠈
    (1, 2): 1 << 4,  # ⠐
    (1, 1): 1 << 5,  # ⠠
    (1, 0): 1 << 7,  # ⢀
    (0, -1): 0,
    (1, -1): 0,
}
coords_braille_mapping_filled: Final[dict[tuple[int, int], int]] = {
    (0, 3): 1 << 0 | 1 << 1 | 1 << 2 | 1 << 6,  # ⡇
    (0, 2): 1 << 1 | 1 << 2 | 1 << 6,  # ⡆
    (0, 1): 1 << 2 | 1 << 6,  # ⡄
    (0, 0): 1 << 6,  # ⡀
    (1, 3): 1 << 3 | 1 << 4 | 1 << 5 | 1 << 7,  # ⢸
    (1, 2): 1 << 4 | 1 << 5 | 1 << 7,  # ⢰
    (1, 1): 1 << 5 | 1 << 7,  # ⢠
    (1, 0): 1 << 7,  # ⢀
    (0, -1): 0,
    (1, -1): 0,
}
