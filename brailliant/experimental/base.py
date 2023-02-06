from __future__ import annotations
import codecs
import math
import string
import stringprep
import time
from codecs import Codec

from codecs import Codec
from itertools import islice

import bitstring as bitstring
from typing import Iterable

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


def reorder_bits(b: int, indices: Iterable[int]) -> int:
    """Reorder the bits of a byte according to the given indices."""
    result = 0
    for i, index in enumerate(indices):
        result |= ((b >> index) & 1) << i
    return result


def get_translation_table() -> bytes:
    translation_table = bytes.maketrans(
        bytes(reorder_bits(i, reversed((0, 3, 1, 4, 2, 5, 6, 7))) for i in range(256)),
        bytes(range(256)),
    )
    return translation_table


#   We don't need to calculate it every time, so instead of doing
#     braille_offset_table = get_translation_table()
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
            "⠀⢀⡀⣀⠠⢠⡠⣠⠄⢄⡄⣄⠤⢤⡤⣤⠐⢐⡐⣐⠰⢰⡰⣰⠔⢔⡔⣔⠴⢴⡴⣴⠂⢂⡂⣂⠢⢢⡢⣢⠆⢆⡆⣆⠦⢦⡦⣦⠒⢒⡒⣒⠲⢲⡲⣲⠖⢖⡖⣖⠶⢶⡶⣶⠈⢈⡈⣈⠨⢨⡨⣨⠌⢌⡌⣌⠬⢬⡬⣬"
            "⠘⢘⡘⣘⠸⢸⡸⣸⠜⢜⡜⣜⠼⢼⡼⣼⠊⢊⡊⣊⠪⢪⡪⣪⠎⢎⡎⣎⠮⢮⡮⣮⠚⢚⡚⣚⠺⢺⡺⣺⠞⢞⡞⣞⠾⢾⡾⣾⠁⢁⡁⣁⠡⢡⡡⣡⠅⢅⡅⣅⠥⢥⡥⣥⠑⢑⡑⣑⠱⢱⡱⣱⠕⢕⡕⣕⠵⢵⡵⣵"
            "⠃⢃⡃⣃⠣⢣⡣⣣⠇⢇⡇⣇⠧⢧⡧⣧⠓⢓⡓⣓⠳⢳⡳⣳⠗⢗⡗⣗⠷⢷⡷⣷⠉⢉⡉⣉⠩⢩⡩⣩⠍⢍⡍⣍⠭⢭⡭⣭⠙⢙⡙⣙⠹⢹⡹⣹⠝⢝⡝⣝⠽⢽⡽⣽⠋⢋⡋⣋⠫⢫⡫⣫⠏⢏⡏⣏⠯⢯⡯⣯"
            "⠛⢛⡛⣛⠻⢻⡻⣻⠟⢟⡟⣟⠿⢿⡿⣿"
        )
    }
)
coords_to_braille = {
    (0, 0): 0b00000010,
    (0, 1): 0b00001000,
    (0, 2): 0b00100000,
    (0, 3): 0b10000000,
    (1, 0): 0b00000001,
    (1, 1): 0b00000100,
    (1, 2): 0b00010000,
    (1, 3): 0b01000000,
}


# def show(ch: int) -> str:
#     return f"{braille_table_str[ch]}  {ch:08b}"
#
#
# print(show(0b10101101))
# print("")
# print(show(0b11101111))
#
#
# print(f"{braille_coords[(1,3)]=}")
# print(f"{show(braille_coords[(1,3)])=}")
# print(f"{show(braille_coords[(0,3)])=}")
# print(f"{show(braille_coords[(1,2)])=}")
#
# exit()
#
#
# def extract_bits(b: bytes | int) -> bytes:
#     if isinstance(b, int):
#         b = b.to_bytes(math.ceil(b.bit_length() / 8), "big")
#
#     bs = []
#     all_bytes = bitstring.BitArray(b)
#
#     for offset in range(0, 4):
#         total = bitstring.BitArray()
#         for b in range(0, 4, 1):
#             l = all_bytes[b * 8 : (b + 1) * 8]
#             part = l[offset * 2 : (offset + 1) * 2]
#             total.append(part)
#         bs.append(total)
#     return b"".join([b.tobytes() for b in bs])
#
#
# def brailleify_4(b: bytes | int, width: int) -> str:
#     if isinstance(b, int):
#         b = b.to_bytes(math.ceil(b.bit_length() / 8), "big")
#
#     bs = []
#     all_bytes = bitstring.BitArray(b)
#
#     for offset in range(0, 4):
#         total = bitstring.BitArray()
#         for b in range(0, width, 1):
#             l = all_bytes[b * 8 : (b + 1) * 8]
#             part = l[offset * 2 : (offset + 1) * 2]
#             total.append(part)
#         bs.append(total.uint)
#     return "".join(braille_table_str.get(c) for c in bs)
#
#
# def brailleify(b: bytes | int, width: int) -> str:
#     if isinstance(b, int):
#         b = b.to_bytes(math.ceil(b.bit_length() / 8), "big")
#
#     bs = []
#     all_bytes = bitstring.BitArray(b)
#     ln = len(all_bytes) // 8
#     for line in range(0, ln // 2, width):
#         for offset in range(0, 4):
#             total = bitstring.BitArray()
#             for b in range(0, width // 2, 1):
#                 l = all_bytes[line * b * 8 : (line * b + 1) * 8]
#                 part = l[offset * 2 : (offset + 1) * 2]
#                 total.append(part)
#             bs.extend(total.tobytes())
#
#     lines = [
#         "".join(braille_table_str.get(c) for c in bs[i : i + width])
#         for i in range(0, len(bs), width)
#     ]
#     return "\n".join(lines)
#
#     return "".join(braille_table_str.get(c) for c in bs)
#
#
# if __name__ == "__live_coding__" or __name__ == "__main__":
#
#     im_4 = 0b11111111_10000001_10000001_11111111_11111111_10000001_10000001_11111111
#
#     # fmt: off
#     im_8 = (
#           0b11111111_11111111_11111111_11111111_11111111_11111111_11111111_11111111 << 32
#         | 0b11111111_10000001_10000001_11111111_11111111_10000001_10000001_11111111
#     )
#
#     im_16 = (
#           0b11111111_11111111_11111111_11111111_11111111_11111111_11111111_11111111 << 96
#         | 0b11111111_10000001_10000001_11111111_11111111_10000001_10000001_11111111 << 64
#         | 0b11111111_10000001_10000001_11111111_11111111_10000001_10000001_11111111 << 32
#         | 0b11111111_11111111_11111111_11111111_11111111_11111111_11111111_11111111
#     )
#     # im_16 = (
#     #     0b11111111_10000001_10000001_11111111_11111111_10000001_10000001_11111111 << 96
#     #     | 0b11111111_10000001_10000001_11111111_11111111_10000001_10000001_11111111 << 64
#     #     | 0b11111111_10000001_10000001_11111111_11111111_10000001_10000001_11111111 << 32
#     #     | 0b11111111_10000001_10000001_11111111_11111111_10000001_10000001_11111111
#     # )
#     # fmt: on
#
#     from PIL import Image
#
#     def get_test_image_box(width: int, height: int) -> Image.Image:
#         test_image_box = Image.new("1", (width, height))
#         for x in range(width):
#             test_image_box.putpixel((x, 0), 1)
#             test_image_box.putpixel((x, height - 1), 1)
#
#         for y in range(height):
#             test_image_box.putpixel((0, y), 1)
#             test_image_box.putpixel((width - 1, y), 1)
#         return test_image_box
#
#     def get_test_image_box_diag(width: int, height: int) -> Image.Image:
#         test_image_box = Image.new("1", (width, height))
#         for x in range(width):
#             test_image_box.putpixel((x, 0), 1)
#             test_image_box.putpixel((x, height - 1), 1)
#
#         for y in range(height):
#             test_image_box.putpixel((0, y), 1)
#             test_image_box.putpixel((width - 1, y), 1)
#             test_image_box.putpixel((y, y), 1)
#         return test_image_box
#
#     def get_test_image_circle(width: int, height: int) -> Image.Image:
#         test_image_circle = Image.new("1", (width, height))
#         center = (width // 2, height // 2)
#         radius = min(width, height) // 3
#         for i in range(360):
#             x = int(center[0] + radius * math.cos(math.radians(i)))
#             y = int(center[1] + radius * math.sin(math.radians(i)))
#             test_image_circle.putpixel((x, y), 1)
#         return test_image_circle
#
#     test_images = [
#         get_test_image_box(8, 8),
#         get_test_image_box(16, 16),
#         get_test_image_box(16, 24),
#         get_test_image_box(24, 16),
#         get_test_image_circle(8, 8),
#         get_test_image_circle(24, 16),
#         get_test_image_box_diag(24, 16),
#         get_test_image_box(32, 32),
#     ]
#
#     for i, test_image in enumerate(test_images):
#         print(f"Image {i}")
#         bit_string = bitstring.BitArray(test_image.tobytes())
#         print(bit_string.bin)  # 1111111110000001100000011000000110000001100000011000000111111111
#
#         rows = [bit_string[i * 8 : (i + 1) * 8] for i in range(len(bit_string) // 8)]
#         for i, row in enumerate(rows):
#             print(row.bin, end=" ")
#             if i % (test_image.width // 8) == test_image.width // 8 - 1:
#                 print()
#
#         bit_strings = [bit_string[i * 8 : (i + 1) * 8] for i in range(len(bit_string) // 8)]
#         result = []
#
#         for y in range(test_image.height):
#             row_bytes = bit_string[y * test_image.width : (y + 1) * test_image.width]
#             print(f"{y:03d} {row_bytes.bin}")
#
#         for y in range(0, test_image.height, 4):
#             row_bytes = [
#                 bit_string[(y + offset) * test_image.width : (y + offset + 1) * test_image.width]
#                 for offset in range(4)
#             ]
#             chars = [[rb[off2 * 2 : (off2 + 1) * 2] for rb in row_bytes] for off2 in range(4)]
#             indv_chars = [[rb for rb in char] for char in chars]
#             b_chars = []
#             for char in indv_chars:
#                 ch = bitstring.BitArray(0)
#                 for c in char:
#                     ch.append(c)
#                 b_chars.append(ch)
#             print(f"{y:03d} {b_chars[0].bin} {b_chars[1].bin} {b_chars[2].bin} {b_chars[3].bin}")
#             result.append([braille_table_str.get(bc.uint) for bc in b_chars])
#         print("\n".join("".join(ln for ln in line) for line in result))
#     #
#     #
#     #
#     # b_chars = [bitstring.BitArray(char) for char in indv_chars]
#     #
#     # # print(f"{y:03d} {[[rb.bin for rb in char] for char in chars]}")
#     # print(f"{y:03d} {[bc.bin for bc in b_chars]}")
#
#     # print(f"x0", [bit_strings[i].bin for i in range(0, len(bit_strings), 2)])
#
#     # print(*[r.bin for r in rows], sep="\n")
#
#     # exit()
#     print(brailleify(test_image.tobytes(), 2))
#     # print(brailleify(im_4, 4))
#     # print(brailleify(im_8, 8))
#     print(brailleify(im_16, 8))
#     print("")
#
#     print(brailleify(extract_bits(im_4), 4))
#     print(brailleify(extract_bits(im_8), 8))
#     print(brailleify(extract_bits(im_16), 16))
#     print("")
#
#     print(brailleify(extract_bits(im_4), 4))
#     print(brailleify(extract_bits(im_8), 8))
#     print(brailleify(extract_bits(im_16), 16))
#     print("")
#
#     print(brailleify(extract_bits(im_4), 4))
#     print(brailleify(extract_bits(im_8), 8))
#     print(brailleify(extract_bits(im_16), 16))
#     print("")
#
#     print(brailleify(extract_bits(im_4), 4))
#     print(brailleify(extract_bits(im_8), 8))
#     print(brailleify(extract_bits(im_16), 16))
#     print("")
#
#     print(brailleify(extract_bits(im_4), 4))
#
#     # t = time.perf_counter()
#     # for _ in range(1000):
#     #     result = brailleify(im)
#     # print(f"Time: {time.perf_counter() - t}; per: {(time.perf_counter() - t) / 1000}")
#     # print(result)
#
#
# # Random interesting symbols:
# # ⋮ 0x22ee
# # ⋯ 0x22ef
# # ⋰ 0x22f0
# # ⋱ 0x22f1
# # ∴ 0x2234
# # ∵ 0x2235
# # ∶ 0x2236
# # ∷ 0x2237
# # ⋅ 0x22c5
# # ⊢ 0x22a2
# # ⊣ 0x22a3
# # ⊤ 0x22a4
# # ⊥ 0x22a5
# # ⟜⊸ ⫰⫯⊷ ⊶
#
#
# # ⟘⟙⟚⟛⟜⟝⟞⟟⟤⟥⟂⟊⟜⟊⟞⟘⊶⊷⧂⧃⦙⦀⦁⦂⫞⫟⫰⫱⫲⫳⫴⫵⫶⫠⫡⫢⫣⫤⫥⫦⫧⫨⫩⫪⫫⫬⫭⫮⫯
#
#
# # ⊶ 0x22b6
# # ⊷ 0x22b7
# # ⊸ 0x22b8
# # ⊹ 0x22b9
# #
# #
# # class BrailleCodec(Codec):
# #     def __init__(self, *args, **kwargs) -> None:
# #         print(f"init braille codec with {args} {kwargs}")
# #
# #     def encode(self, input_str: str, errors: str = "strict") -> tuple[bytes, int]:
# #         chars = list(input_str)
# #
# #         output_bytes = []
# #         for char in chars:
# #             # Get the Unicode code point of the character
# #             code_point = ord(char)
# #             # Subtract 0x2800 to get the code point in the ASCII range
# #             code_point -= 0x2800
# #             # Translate the code point to the standard order of bits
# #             output_bytes.append(bytes((code_point,)).translate(braille_table))
# #
# #         # Return the encoded bytes and the number of characters processed
# #         return b"".join(output_bytes), len(chars)
# #
# #     def decode(self, input_bytes: bytes, errors: str = "strict") -> tuple[str, int]:
# #         # Decode each byte as a character using the braille_table translation table
# #         output_str = [chr(bytes((b,)).translate(braille_table)[0] | 0x2800) for b in input_bytes]
# #         return "".join(output_str), len(input_bytes)
# #
# #
# # braille_codec_info = codecs.CodecInfo(
# #     name="braille",
# #     encode=BrailleCodec().encode,
# #     decode=BrailleCodec().decode,
# #     incrementalencoder=None,  # codecs.IncrementalEncoder,
# #     incrementaldecoder=None,  # codecs.IncrementalDecoder,
# #     streamreader=None,  # codecs.StreamReader,
# #     streamwriter=None,  # codecs.StreamWriter,
# # )
# #
# # input_str = "⢠⢁⠉⣹⢠⢁⠉⣹⢠⢁⠉⣹"
# # encoded_bytes = input_str.encode()
# # print(encoded_bytes)
# #
# #
# # codecs.register(lambda name: braille_codec_info if name == "braille" else None)
# #
# #
# # str_trans = str.maketrans(
# #     {b: chr(bytes((b,)).translate(braille_table)[0] | 0x2800) for b in range(256)}
# # )
# # text = b"\x00\x01ello, world!".decode()
# # translated_text = text.translate(str_trans)
# # print(translated_text)
# #
# # s = "\xe2\xa2\xa0\xe2\xa2\x81\xe2\xa0\xa2\x81\xe2\xa0\x89\xe2\xa3\xb9"
# # print(s.translate(str_trans))
# #
# # b = "".join("\x00".translate(str_trans))
# #
# # t = time.perf_counter()
# # for _ in range(100000):
# #     encoded_bytes.decode("braille")
# # print(f"decode time: {time.perf_counter() - t}")
# #
# # t = time.perf_counter()
# # for _ in range(100000):
# #     "".join([chr(bytes((b,)).translate(braille_table)[0] | 0x2800) for b in encoded_bytes])
# # print(f"braille_table: {time.perf_counter() - t}")
# #
# #
# # table = {
# #     chr(bytes((b,)).translate(braille_table)[0] | 0x2800): bytes((b,)).translate(braille_table)
# #     for b in range(256)
# # }
# # print(table)
# # t = time.perf_counter()
# # for _ in range(100000):
# #     "".join("\x00".translate(table))
# # print(f"translating: {time.perf_counter() - t}")
# #
# # print(table)
# # t = time.perf_counter()
# # for _ in range(100000):
# #     c = encoded_bytes.decode().translate(str_trans)
# # print(f"str_trans: {time.perf_counter() - t}")
# # print(f"stranslate: {c}")
# #
# #
# # # Decode the encoded bytes as a string using the Braille codec
# # decoded_str = encoded_bytes.decode(encoding="braille")
# # print(decoded_str)  # prints ⢠
# # print(b"\xf0\x0f".decode(encoding="braille"))  # prints b'\x1e\x1a\x1a\x1c\x1e\x1a\x1a\x1e\x1c\x1e'
# # print(bytes((0b10000001, 0b11000000, 0b0011010111)).decode(encoding="braille"))  # prints ⢁⠉⣹
# # print(bytes((0b10000001, 0b11000000, 0b0011010111)).decode(encoding="braille"))  # prints ⢁⠉⣹
# #
# # encoded = "⢁⠉⣹".encode(encoding="braille")
# # print(encoded)  # prints b'\x81\x84\x9f'
# # print(encoded.decode(encoding="braille"))  # prints ⢁⠉⣹
# #
# #
# # def extract_bits(b: bytes | int) -> bytes:
# #     if isinstance(b, int):
# #         b = b.to_bytes(math.ceil(b.bit_length() / 8), "big")
# #         print(f"new b: {b}")
# #
# #     bs = []
# #     all_bytes = bitstring.BitArray(b)
# #
# #     for offset in range(0, 4):
# #         total = bitstring.BitArray()
# #         for b in range(0, 4, 1):
# #             l = all_bytes[b * 8 : (b + 1) * 8]
# #             part = l[offset * 2 : (offset + 1) * 2]
# #             total.append(part)
# #             print(total.bin)
# #         bs.append(total)
# #     return b"".join([b.tobytes() for b in bs])
# #
# #
# # if __name__ == "__main__":
# #
# #     im = 0b11111111_10000001_10000001_11111111_11111111_10000001_10000001_11111111
# #     as_bytes = extract_bits(im)
# #     result = as_bytes.decode().translate(braille_table_str)
# #     print("result", result)
# #
# # if __name__ == "__main__":
# #
# #     # Mapping bytes through the translation table:
# #
# #     # 0b 1 0
# #     # 0b 0 0
# #     # 0b 0 0
# #     # 0b 0 1
# #     # aka 0b10000001
# #     # aka top left + bottom right
# #     # aka ⢁
# #     print(f"{chr(braille_table[0b10000001] + 0x2800)}")
# #
# #     # 0b 1 0
# #     # 0b 1 0
# #     # 0b 0 1
# #     # 0b 0 1
# #     # aka 0b10100101
# #     # aka half line on top left + half line on bottom right
# #     # aka ⢣
# #     print(f"{chr(braille_table[0b10100101] + 0x2800)}")
# #
# #     print(hex(0b10100101))  # 0xa5
# #     print(hex(0b10000001))  # 0x81
# #     print(hex(0b01000010))  # 0x42
# #     print(hex(0b00111100))  # 0x3c
# #     print(b"\xa5\x81".translate(braille_table))  # b'\xa3\x81'
# #
# #     chars = (0x2800 | ch for ch in b"\xa5\x81\x42\x3c".translate(braille_table))
# #     print("".join(chr(ch) for ch in chars))  # ⢣⢁⡈⠶
# #
# braille_coords = {
#     (0, 0): 1 << 8,
#     (0, 1): 1 << 6,
#     (0, 2): 1 << 4,
#     (0, 3): 1 << 2,
#     (1, 0): 1 << 7,
#     (1, 1): 1 << 5,
#     (1, 2): 1 << 3,
#     (1, 3): 1 << 1,
# }
# #
# #
# # def coords_to_braille(*coords: tuple[int, int]) -> str:
# #     """Convert a set of coordinates to a braille character."""
# #     binary = 0
# #     for x, y in coords:
# #         binary |= braille_coords[(x, y)]
# #
# #     ch = binary.to_bytes(1, "little").translate(braille_table)
# #     assert isinstance(ch, int)
# #     return chr(ch | 0x2800)
# #
# #
# # print(coords_to_braille((0, 0), (0, 1), (0, 2), (0, 3)))
#
# print(brailleify(b"\x01\x00\x00\x00\x00\x00\x00\x01\x01\x01\x01\x01", 2))


__all__ = (
    "BRAILLE_RANGE_START",
    "coords_braille_mapping",
    "coords_braille_mapping_filled",
    # "brailleify",
    "coords_to_braille",
)
