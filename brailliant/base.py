import operator
from functools import reduce
from typing import Final

from bitarray import bitarray

BRAILLE_COLS: Final[int] = 2
BRAILLE_ROWS: Final[int] = 4

BRAILLE_RANGE_START: Final[int] = 0x2800

CHAR_HEIGHT: Final[int] = BRAILLE_ROWS
CHAR_WIDTH: Final[int] = BRAILLE_COLS


# Unicode braille:
#  0 3
#  1 4
#  2 5
#  6 7

# Desired:
#  0 1
#  2 3
#  4 5
#  6 7

# Where the bits are:
#  0b01234567

# def _reorder_bits(b: int, indices: Iterable[int]) -> int:
#     """Reorder the bits of a byte according to the given indices."""
#     result = 0
#     for i, index in enumerate(indices):
#         result |= ((b >> index) & 1) << i
#     return result
#
#
# def _get_translation_table() -> bytes:
#     translation_table = bytes.maketrans(
#         bytes(_reorder_bits(i, reversed((0, 3, 1, 4, 2, 5, 6, 7))) for i in range(256)),
#         bytes(range(256)),
#     )
#     return translation_table


#   We don't need to calculate it every time, so instead of doing
#     braille_offset_table = _get_translation_table()
#   we can just do:
# braille_table = (
#     b"\x00\x80@\xc0 \xa0`\xe0\x04\x84D\xc4$\xa4d\xe4\x10\x90P\xd00\xb0p\xf0\x14\x94"
#     b'T\xd44\xb4t\xf4\x02\x82B\xc2"\xa2b\xe2\x06\x86F\xc6&\xa6f\xe6\x12\x92R\xd22'
#     b"\xb2r\xf2\x16\x96V\xd66\xb6v\xf6\x08\x88H\xc8(\xa8h\xe8\x0c\x8cL\xcc,\xacl"
#     b"\xec\x18\x98X\xd88\xb8x\xf8\x1c\x9c\\\xdc<\xbc|\xfc\n\x8aJ\xca*\xaaj\xea\x0e"
#     b"\x8eN\xce.\xaen\xee\x1a\x9aZ\xda:\xbaz\xfa\x1e\x9e^\xde>\xbe~\xfe\x01\x81A"
#     b"\xc1!\xa1a\xe1\x05\x85E\xc5%\xa5e\xe5\x11\x91Q\xd11\xb1q\xf1\x15\x95U\xd55"
#     b"\xb5u\xf5\x03\x83C\xc3#\xa3c\xe3\x07\x87G\xc7'\xa7g\xe7\x13\x93S\xd33\xb3s"
#     b"\xf3\x17\x97W\xd77\xb7w\xf7\t\x89I\xc9)\xa9i\xe9\r\x8dM\xcd-\xadm\xed\x19"
#     b"\x99Y\xd99\xb9y\xf9\x1d\x9d]\xdd=\xbd}\xfd\x0b\x8bK\xcb+\xabk\xeb\x0f\x8fO"
#     b"\xcf/\xafo\xef\x1b\x9b[\xdb;\xbb{\xfb\x1f\x9f_\xdf?\xbf\x7f\xff"
# )

# We can create a string translation table from the bytes translation table:
#     braille_table_str = str.maketrans(
#         {b: chr(bytes((b,)).translate(braille_table)[0] | 0x2800) for b in range(256)}
#     )
# Again, we don't need to calculate it every time, so we'll just do:

braille_table_str = str.maketrans(
    {
        i: c
        for i, c in enumerate(
            "⠀⢀⡀⣀⠠⢠⡠⣠⠄⢄⡄⣄⠤⢤⡤⣤"
            "⠐⢐⡐⣐⠰⢰⡰⣰⠔⢔⡔⣔⠴⢴⡴⣴"
            "⠂⢂⡂⣂⠢⢢⡢⣢⠆⢆⡆⣆⠦⢦⡦⣦"
            "⠒⢒⡒⣒⠲⢲⡲⣲⠖⢖⡖⣖⠶⢶⡶⣶"
            "⠈⢈⡈⣈⠨⢨⡨⣨⠌⢌⡌⣌⠬⢬⡬⣬"
            "⠘⢘⡘⣘⠸⢸⡸⣸⠜⢜⡜⣜⠼⢼⡼⣼"
            "⠊⢊⡊⣊⠪⢪⡪⣪⠎⢎⡎⣎⠮⢮⡮⣮"
            "⠚⢚⡚⣚⠺⢺⡺⣺⠞⢞⡞⣞⠾⢾⡾⣾"
            "⠁⢁⡁⣁⠡⢡⡡⣡⠅⢅⡅⣅⠥⢥⡥⣥"
            "⠑⢑⡑⣑⠱⢱⡱⣱⠕⢕⡕⣕⠵⢵⡵⣵"
            "⠃⢃⡃⣃⠣⢣⡣⣣⠇⢇⡇⣇⠧⢧⡧⣧"
            "⠓⢓⡓⣓⠳⢳⡳⣳⠗⢗⡗⣗⠷⢷⡷⣷"
            "⠉⢉⡉⣉⠩⢩⡩⣩⠍⢍⡍⣍⠭⢭⡭⣭"
            "⠙⢙⡙⣙⠹⢹⡹⣹⠝⢝⡝⣝⠽⢽⡽⣽"
            "⠋⢋⡋⣋⠫⢫⡫⣫⠏⢏⡏⣏⠯⢯⡯⣯"
            "⠛⢛⡛⣛⠻⢻⡻⣻⠟⢟⡟⣟⠿⢿⡿⣿"
        )
    }
)

# Mapping of (x, y) coordinates to braille character dots represented as a bit mask.
# The resulting integer of one of these values or an OR of multiple of them will result
# in the index of the braille character in the braille_table_str table.
# By bit masking many (x, y) coordinates, we can get a single braille character with dots
# set at each of the (x, y) coordinates.
# For instance -
#
# |               Access                    | Decimal | braille_table_str[Decimal] |
# | coords_braille_mapping[(0, 0)]          |       2 |                          ⡀ |
# | coords_braille_mapping[(1, 0)]          |       1 |                          ⢀ |
# | cbm[(0, 0)] | cbm[(1, 0)]               |       3 |                          ⣀ |
# | cbm[(0, 0)] | cbm[(1, 0)] | cbm[(1, 2)] |      19 |                          ⣐ |
coords_braille_mapping = {
    (0, 0): 0b00000010,
    (0, 1): 0b00001000,
    (0, 2): 0b00100000,
    (0, 3): 0b10000000,
    (1, 0): 0b00000001,
    (1, 1): 0b00000100,
    (1, 2): 0b00010000,
    (1, 3): 0b01000000,
}

# Used for "filled area chart" - these mappings represent coords to the braille characters
# with the dots below a given y position filled in. That is:
# (0, 0) 2      ⡀
# (0, 1) 10     ⡄
# (0, 2) 42     ⡆
# (0, 3) 170    ⡇
# (1, 0) 1      ⢀
# (1, 1) 5      ⢠
# (1, 2) 21     ⢰
# (1, 3) 85     ⢸
coords_braille_mapping_filled = {
    (x, y): reduce(operator.or_, [coords_braille_mapping[(x, yy)] for yy in range(y + 1)], 0)
    for x in range(2)
    for y in range(4)
}


def coords_to_braille(*coords: tuple[int, int], filled: bool = False) -> str:
    """Converts a tuple of coordinates to a braille character.

    Args:
        coords: Coordinates to convert.
        filled: Whether to fill in the dots below the given y coordinate.

    Returns:
        A braille character with the dots set at the given coordinates.

    Examples:
        >>> coords_to_braille((0, 0))
        '⡀'

        >>> coords_to_braille((0, 0), (1, 0))
        '⣀'

        >>> coords_to_braille((0, 3), (1, 1), (1, 0))
        '⢡'

        >>> coords_to_braille((0, 3), (1, 1), (1, 0), filled=True)
        '⣧'
    """
    mapping = coords_braille_mapping_filled if filled else coords_braille_mapping
    braille_char = 0
    for coord in coords:
        braille_char |= mapping[coord]
    return braille_table_str[braille_char]


# Mapping of characters to the more efficient bitarray representation
braille_table_bitarray = {
    c.encode(): bitarray(format(i, "08b"))
    for i, c in enumerate(
        "⠀⢀⡀⣀⠠⢠⡠⣠⠄⢄⡄⣄⠤⢤⡤⣤"
        "⠐⢐⡐⣐⠰⢰⡰⣰⠔⢔⡔⣔⠴⢴⡴⣴"
        "⠂⢂⡂⣂⠢⢢⡢⣢⠆⢆⡆⣆⠦⢦⡦⣦"
        "⠒⢒⡒⣒⠲⢲⡲⣲⠖⢖⡖⣖⠶⢶⡶⣶"
        "⠈⢈⡈⣈⠨⢨⡨⣨⠌⢌⡌⣌⠬⢬⡬⣬"
        "⠘⢘⡘⣘⠸⢸⡸⣸⠜⢜⡜⣜⠼⢼⡼⣼"
        "⠊⢊⡊⣊⠪⢪⡪⣪⠎⢎⡎⣎⠮⢮⡮⣮"
        "⠚⢚⡚⣚⠺⢺⡺⣺⠞⢞⡞⣞⠾⢾⡾⣾"
        "⠁⢁⡁⣁⠡⢡⡡⣡⠅⢅⡅⣅⠥⢥⡥⣥"
        "⠑⢑⡑⣑⠱⢱⡱⣱⠕⢕⡕⣕⠵⢵⡵⣵"
        "⠃⢃⡃⣃⠣⢣⡣⣣⠇⢇⡇⣇⠧⢧⡧⣧"
        "⠓⢓⡓⣓⠳⢳⡳⣳⠗⢗⡗⣗⠷⢷⡷⣷"
        "⠉⢉⡉⣉⠩⢩⡩⣩⠍⢍⡍⣍⠭⢭⡭⣭"
        "⠙⢙⡙⣙⠹⢹⡹⣹⠝⢝⡝⣝⠽⢽⡽⣽"
        "⠋⢋⡋⣋⠫⢫⡫⣫⠏⢏⡏⣏⠯⢯⡯⣯"
        "⠛⢛⡛⣛⠻⢻⡻⣻⠟⢟⡟⣟⠿⢿⡿⣿"
    )
}
