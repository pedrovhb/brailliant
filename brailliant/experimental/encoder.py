import sys

braille_length = len(chr(0x2800).encode())
bs = int.from_bytes("⢠⢀".encode(), sys.byteorder)
bs = int.from_bytes("⢠⢀".encode(), sys.byteorder)
delta = int.from_bytes(chr(0x2800).encode(), sys.byteorder) - int.from_bytes(
    "⠁".encode(), sys.byteorder
)
print(delta)


def to_braille(i: int) -> str:
    return i.to_bytes((i.bit_length() // 8) * 3, sys.byteorder).decode()


bbase = int.from_bytes(chr(0x2800).encode(), sys.byteorder)
print(to_braille(bbase + (1 << 8) + (1 << 9)))  # ⣀
print(to_braille(bbase | (1 << 8)))  # ⡀
print(to_braille(bbase + 1024))  # returns ⤀

print(bbase := int.from_bytes(chr(0x2800).encode(), sys.byteorder))
print(bin(bbase))
print(bin(bbase + 1))
print(bin(bs))
print(bs)
print(to_braille(bs))
print(2**16)
print(to_braille(bbase | (8 << 2)))


codepoint = int.from_bytes("⢠⠁".encode(), sys.byteorder)
b = (
    0xE0
    | (codepoint >> 12)
    | (0x80 | ((codepoint >> 6) & 0x3F)) << 8
    | (0x80 | (codepoint & 0x3F)) << 16
)

b
# 8691938

b.to_bytes(3, sys.byteorder).decode()
# '⠄'
# "⢠⢀"
