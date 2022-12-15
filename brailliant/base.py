from __future__ import annotations


BRAILLE_RANGE_START = 0x2800

coords_braille_mapping = {
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
coords_braille_mapping_filled = {
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


def coords_to_braille(*coords: tuple[int, int]) -> str:
    """Convert a set of coordinates to a single braille character.

    It accepts a variable number of (x, y) coordinates, and returns a single braille character
    representing the union of the coordinates.

    The coordinates are relative to the bottom left of the braille character, with the x-axis
    going right and the y-axis going up. They must be integers in the range [0, 1] for x, and
     [-1, 3] for y.

    [0, 0] is the bottom left of the braille character, and [1, 3] is the top right. Values
    [0, -1] and [1, -1] are ignored. Other values are invalid and will raise a ValueError.


    Args:
        coords: One or more (x, y) coordinates.

    Returns:
        A single braille character.

    Examples:
        >>> coords_to_braille((0, 0))
        '⡀'

        >>> coords_to_braille((0, 0), (1, 0))
        '⣀'

        >>> coords_to_braille((0, 0), (1, 0), (0, 1))
        '⣄'

    Raises:
        ValueError: If any of the coordinates are out of range.
    """
    result = BRAILLE_RANGE_START
    for coord in coords:
        if coord not in coords_braille_mapping:
            raise ValueError(f"Invalid coordinate: {coord}")
        result |= coords_braille_mapping[coord]
    return chr(result)


__all__ = (
    "BRAILLE_RANGE_START",
    "coords_braille_mapping",
    "coords_braille_mapping_filled",
    "coords_to_braille",
)
