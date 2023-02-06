import itertools
import random
import re
import time
from itertools import chain

from itertools import *
from bitarray import bitarray


# Conclusion:


# bits_2_8 = (
#     0b11111010_10101010_01010101_11010101_11111111_11111111_00000000_00000000_10101010_10101010_01010101_01010101_11111111_11111111_00000000_00000000
#     0        1        2        3        4        5        6        7        8        9        10       11       12       13       14       15
# )
r = random.randint(2, 2**64)
str_table = (
    "⠀⢀⡀⣀⠠⢠⡠⣠⠄⢄⡄⣄⠤⢤⡤⣤⠐⢐⡐⣐⠰⢰⡰⣰⠔⢔⡔⣔⠴⢴⡴⣴⠂⢂⡂⣂⠢⢢⡢⣢⠆⢆⡆⣆⠦⢦⡦⣦⠒⢒⡒⣒⠲⢲⡲⣲⠖⢖⡖⣖⠶⢶⡶⣶⠈⢈⡈⣈⠨⢨⡨⣨⠌⢌⡌⣌⠬⢬⡬⣬"
    "⠘⢘⡘⣘⠸⢸⡸⣸⠜⢜⡜⣜⠼⢼⡼⣼⠊⢊⡊⣊⠪⢪⡪⣪⠎⢎⡎⣎⠮⢮⡮⣮⠚⢚⡚⣚⠺⢺⡺⣺⠞⢞⡞⣞⠾⢾⡾⣾⠁⢁⡁⣁⠡⢡⡡⣡⠅⢅⡅⣅⠥⢥⡥⣥⠑⢑⡑⣑⠱⢱⡱⣱⠕⢕⡕⣕⠵⢵⡵⣵"
    "⠃⢃⡃⣃⠣⢣⡣⣣⠇⢇⡇⣇⠧⢧⡧⣧⠓⢓⡓⣓⠳⢳⡳⣳⠗⢗⡗⣗⠷⢷⡷⣷⠉⢉⡉⣉⠩⢩⡩⣩⠍⢍⡍⣍⠭⢭⡭⣭⠙⢙⡙⣙⠹⢹⡹⣹⠝⢝⡝⣝⠽⢽⡽⣽⠋⢋⡋⣋⠫⢫⡫⣫⠏⢏⡏⣏⠯⢯⡯⣯"
    "⠛⢛⡛⣛⠻⢻⡻⣻⠟⢟⡟⣟⠿⢿⡿⣿"
)


def impl_a(bits, w_bytes, h_bytes):
    ba_2_8 = bitarray(buffer=bits.to_bytes(w_bytes * h_bytes * 8, "big"))
    zipped_array = bitarray(chain.from_iterable(zip(ba_2_8[::8], ba_2_8[1::8])))
    return "".join([str_table[b] for b in zipped_array.tobytes()])


n_runs = 10000
print(r)
t = time.perf_counter()
for i in range(n_runs):
    r = random.randint(2, 2**64)
    impl_a(r, 1, r.bit_length() // 8)
print(f"{impl_a.__name__}: {(time.perf_counter() - t)/n_runs:.8f}s")
print(impl_a(r, 8, 8))

# fmt: off

bits_2_2 = 0b10101010_10101010_01010101_01010101
#            abcdefgh_ijklmnop_ABCDEFGH_IJKLMNOP
bits_2_4 = 0b10101010_10101010_10101010_10101010_11111111_11111111_00000000_00000000
#            abcdefgh_ijklmnop_ABCDEFGH_IJKLMNOP_abcdefgh_ijklmnop_ABCDEFGH_IJKLMNOP

bits_ch_2_2 = "abcdefgh" "ijklmnop" "qrstuvwx" "yz012345"


bits_ch_1_8 = (
    "abcdefgh" "ijklmnop" "qrstuvwx" "yz012345" "ABCDEFGH" "IJKLMNOP" "QRSTUVWX" "YZ6789!@"
)

# First char, first line:
print(bits_ch_1_8[0:2])     # ab
print(bits_ch_1_8[8:10])    # ij
print(bits_ch_1_8[16:18])   # qr
print(bits_ch_1_8[24:26])   # yz

# Second char, first line:
print(bits_ch_1_8[2:4])     # cd
print(bits_ch_1_8[10:12])   # kl
print(bits_ch_1_8[18:20])   # st
print(bits_ch_1_8[26:28])   # 01

# Third char, first line:
print(bits_ch_1_8[4:6])     # ef
print(bits_ch_1_8[12:14])   # mn
print(bits_ch_1_8[20:22])   # uv
print(bits_ch_1_8[28:30])   # 23

# Fourth char, first line:
print(bits_ch_1_8[6:8])     # gh
print(bits_ch_1_8[14:16])   # op
print(bits_ch_1_8[22:24])   # wx
print(bits_ch_1_8[30:32])   # 45

# Fifth char, first line:
print(bits_ch_1_8[32:34])
print(bits_ch_1_8[40:42])
print(bits_ch_1_8[48:50])
print(bits_ch_1_8[56:58])

# Sixth char, first line:
print(bits_ch_1_8[34:36])
print(bits_ch_1_8[42:44])
print(bits_ch_1_8[50:52])
print(bits_ch_1_8[58:60])

# Seventh char, first line:
print(bits_ch_1_8[36:38])
print(bits_ch_1_8[44:46])
print(bits_ch_1_8[52:54])
print(bits_ch_1_8[60:62])

# Eighth char, first line:
print(bits_ch_1_8[38:40])
print(bits_ch_1_8[46:48])
print(bits_ch_1_8[54:56])
print(bits_ch_1_8[62:64])


# The following function generalizes the above:
def get_char_from_bits_ch_1_8(line, char):
    """
    Get the character at the given line and character position from the
    bits_ch_1_8 string.
    """
    return bits_ch_1_8[(line * 8 + char) * 2 : (line * 8 + char + 1) * 2]


print(get_char_from_bits_ch_1_8(0, 0))  # ab
print(get_char_from_bits_ch_1_8(0, 1))  # cd
print(get_char_from_bits_ch_1_8(0, 2))  # ef
print(get_char_from_bits_ch_1_8(0, 3))  # gh

# Complete chars:
print(bits_ch_1_8[0:2] + bits_ch_1_8[8:10] + bits_ch_1_8[16:18] + bits_ch_1_8[24:26])   # 'abijqryz'
print(bits_ch_1_8[2:4] + bits_ch_1_8[10:12] + bits_ch_1_8[18:20] + bits_ch_1_8[26:28])  # 'cdklst01'
print(bits_ch_1_8[4:6] + bits_ch_1_8[12:14] + bits_ch_1_8[20:22] + bits_ch_1_8[28:30])  # 'efmnuv23'
print(bits_ch_1_8[6:8] + bits_ch_1_8[14:16] + bits_ch_1_8[22:24] + bits_ch_1_8[30:32])  # 'ghopwx45'


# The following function generalizes the above:
def get_chars_from_bits_ch_1_8(line):
    """
    Get the characters at the given line from the bits_ch_1_8 string.
    """
    chs = []
    for char in range(4):
        chs.append(bits_ch_1_8[(line * 8 + char) * 2 : (line * 8 + char + 1) * 2])
    return "".join(chs)


print(get_chars_from_bits_ch_1_8(0))  # 'abijqryz'
print(get_chars_from_bits_ch_1_8(1))  # 'cdklst01'
print(get_chars_from_bits_ch_1_8(2))  # 'efmnuv23'
print(get_chars_from_bits_ch_1_8(3))  # 'ghopwx45'


# equivalent, but with bits/bytes:
bits_1_8 = (
    0b10101010_10101010_01010101_01010101_11111111_11111111_00000000_00000000
)
bits_2_8 = (
    0b11111010_10101010_01010101_11010101_11111111_11111111_00000000_00000000_10101010_10101010_01010101_01010101_11111111_11111111_00000000_00000000
    # 0        1        2        3        4        5        6        7        8        9        10       11       12       13       14       15
)

str_table = (            "⠀⢀⡀⣀⠠⢠⡠⣠⠄⢄⡄⣄⠤⢤⡤⣤⠐⢐⡐⣐⠰⢰⡰⣰⠔⢔⡔⣔⠴⢴⡴⣴⠂⢂⡂⣂⠢⢢⡢⣢⠆⢆⡆⣆⠦⢦⡦⣦⠒⢒⡒⣒⠲⢲⡲⣲⠖⢖⡖⣖⠶⢶⡶⣶⠈⢈⡈⣈⠨⢨⡨⣨⠌⢌⡌⣌⠬⢬⡬⣬"
            "⠘⢘⡘⣘⠸⢸⡸⣸⠜⢜⡜⣜⠼⢼⡼⣼⠊⢊⡊⣊⠪⢪⡪⣪⠎⢎⡎⣎⠮⢮⡮⣮⠚⢚⡚⣚⠺⢺⡺⣺⠞⢞⡞⣞⠾⢾⡾⣾⠁⢁⡁⣁⠡⢡⡡⣡⠅⢅⡅⣅⠥⢥⡥⣥⠑⢑⡑⣑⠱⢱⡱⣱⠕⢕⡕⣕⠵⢵⡵⣵"
            "⠃⢃⡃⣃⠣⢣⡣⣣⠇⢇⡇⣇⠧⢧⡧⣧⠓⢓⡓⣓⠳⢳⡳⣳⠗⢗⡗⣗⠷⢷⡷⣷⠉⢉⡉⣉⠩⢩⡩⣩⠍⢍⡍⣍⠭⢭⡭⣭⠙⢙⡙⣙⠹⢹⡹⣹⠝⢝⡝⣝⠽⢽⡽⣽⠋⢋⡋⣋⠫⢫⡫⣫⠏⢏⡏⣏⠯⢯⡯⣯"
            "⠛⢛⡛⣛⠻⢻⡻⣻⠟⢟⡟⣟⠿⢿⡿⣿")
base_utf8_braille = chr(0x2800).encode('utf-8')
bs_table = {b: chr(0x2800 | b).encode() for b in range(256)}

ba_1_8 = bitarray()
ba_1_8.frombytes(bits_1_8.to_bytes(8, 'big'))
ba_2_8 = bitarray()


str_table = (            "⠀⢀⡀⣀⠠⢠⡠⣠⠄⢄⡄⣄⠤⢤⡤⣤⠐⢐⡐⣐⠰⢰⡰⣰⠔⢔⡔⣔⠴⢴⡴⣴⠂⢂⡂⣂⠢⢢⡢⣢⠆⢆⡆⣆⠦⢦⡦⣦⠒⢒⡒⣒⠲⢲⡲⣲⠖⢖⡖⣖⠶⢶⡶⣶⠈⢈⡈⣈⠨⢨⡨⣨⠌⢌⡌⣌⠬⢬⡬⣬"
            "⠘⢘⡘⣘⠸⢸⡸⣸⠜⢜⡜⣜⠼⢼⡼⣼⠊⢊⡊⣊⠪⢪⡪⣪⠎⢎⡎⣎⠮⢮⡮⣮⠚⢚⡚⣚⠺⢺⡺⣺⠞⢞⡞⣞⠾⢾⡾⣾⠁⢁⡁⣁⠡⢡⡡⣡⠅⢅⡅⣅⠥⢥⡥⣥⠑⢑⡑⣑⠱⢱⡱⣱⠕⢕⡕⣕⠵⢵⡵⣵"
            "⠃⢃⡃⣃⠣⢣⡣⣣⠇⢇⡇⣇⠧⢧⡧⣧⠓⢓⡓⣓⠳⢳⡳⣳⠗⢗⡗⣗⠷⢷⡷⣷⠉⢉⡉⣉⠩⢩⡩⣩⠍⢍⡍⣍⠭⢭⡭⣭⠙⢙⡙⣙⠹⢹⡹⣹⠝⢝⡝⣝⠽⢽⡽⣽⠋⢋⡋⣋⠫⢫⡫⣫⠏⢏⡏⣏⠯⢯⡯⣯"
            "⠛⢛⡛⣛⠻⢻⡻⣻⠟⢟⡟⣟⠿⢿⡿⣿")
w = 2
h = 1
ba_2_8.frombytes(bits_2_8.to_bytes(w * h * 8, "big"))
zipped_array = bitarray(chain.from_iterable(zip(ba_2_8[::8], ba_2_8[1::8])))
string = "".join([str_table[b] for b in zipped_array.tobytes()])

t = time.perf_counter()
for _ in range(10000):
    string = "".join(str_table[b] for b in zipped_array.tobytes())
print(format(time.perf_counter() - t, ".8f"))

t = time.perf_counter()
for _ in range(10000):
    string = b"".join(bs_table[b] for b in zipped_array.tobytes()).decode()
print(format(time.perf_counter() - t, ".8f"))

t = time.perf_counter()
for _ in range(10000):
    string = "".join([str_table[b] for b in zipped_array.tobytes()])
print(format(time.perf_counter() - t, ".8f"))

t = time.perf_counter()
for _ in range(10000):
    string = b"".join([bs_table[b] for b in zipped_array.tobytes()]).decode()
print(format(time.perf_counter() - t, ".8f"))



print(ba_1_8)
print(ba_2_8)

print(ba_1_8[::8])
print(ba_1_8[1::8])

print(ba_2_8[::8])
print(ba_2_8[1::8])

zp = list(zip(ba_2_8[::8], ba_2_8[1::8]))
zp = list(chain.from_iterable(zp))

def chunks(iterable, n):
    """Yield successive n-sized chunks from iterable."""
    for i in range(0, len(iterable), n):
        yield iterable[i : i + n]

print("".join(map(str, chain.from_iterable(chunks(zp, 8)))))
print(chs := bitarray(chain.from_iterable(zip(ba_2_8[::8], ba_2_8[1::8]))))

base_utf8_braille = chr(0x2800).encode('utf-8')
table = {i: base_utf8_braille + i.to_bytes(1, 'big') for i in range(256)}

s = (            "⠀⢀⡀⣀⠠⢠⡠⣠⠄⢄⡄⣄⠤⢤⡤⣤⠐⢐⡐⣐⠰⢰⡰⣰⠔⢔⡔⣔⠴⢴⡴⣴⠂⢂⡂⣂⠢⢢⡢⣢⠆⢆⡆⣆⠦⢦⡦⣦⠒⢒⡒⣒⠲⢲⡲⣲⠖⢖⡖⣖⠶⢶⡶⣶⠈⢈⡈⣈⠨⢨⡨⣨⠌⢌⡌⣌⠬⢬⡬⣬"
            "⠘⢘⡘⣘⠸⢸⡸⣸⠜⢜⡜⣜⠼⢼⡼⣼⠊⢊⡊⣊⠪⢪⡪⣪⠎⢎⡎⣎⠮⢮⡮⣮⠚⢚⡚⣚⠺⢺⡺⣺⠞⢞⡞⣞⠾⢾⡾⣾⠁⢁⡁⣁⠡⢡⡡⣡⠅⢅⡅⣅⠥⢥⡥⣥⠑⢑⡑⣑⠱⢱⡱⣱⠕⢕⡕⣕⠵⢵⡵⣵"
            "⠃⢃⡃⣃⠣⢣⡣⣣⠇⢇⡇⣇⠧⢧⡧⣧⠓⢓⡓⣓⠳⢳⡳⣳⠗⢗⡗⣗⠷⢷⡷⣷⠉⢉⡉⣉⠩⢩⡩⣩⠍⢍⡍⣍⠭⢭⡭⣭⠙⢙⡙⣙⠹⢹⡹⣹⠝⢝⡝⣝⠽⢽⡽⣽⠋⢋⡋⣋⠫⢫⡫⣫⠏⢏⡏⣏⠯⢯⡯⣯"
            "⠛⢛⡛⣛⠻⢻⡻⣻⠟⢟⡟⣟⠿⢿⡿⣿")

a = "".join(s[b] for b in chs.tobytes())
print(a)
# a = int.from_bytes(, "big")

pat = re.compile(rb".")
print(pat.sub(lambda match: s[int(match.group(0))], bits_2_8.to_bytes(16, 'big')))

for i, b in table.items():
    print(i, b.decode('utf-8'))


print(base_utf8_braille.hex())
print(0x80 - 0xff)
a = int.from_bytes(base_utf8_braille, 'big')
baa = bitarray.frombytes(a + n for n in chain.from_iterable(zip(ba_2_8[::8], ba_2_8[1::8])))
print(baa.tobytes())

chars = bitarray(chain.from_iterable(zip(ba_2_8[::8], ba_2_8[1::8])))


print(list(chunks(chars, 8)))

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
inv_braille_table = {v: bitarray(format(k, "b")) for k, v in braille_table_str.items()}


b2 = bitarray()
b2.encode(inv_braille_table, "⡃⣃⠣⢣⡣⣣⠇")
bs = b"\x28\x05"

braille_char = "⠁"
print(braille_char == chr(0x2801))  # True
print(braille_char.encode('utf-8'))  # b'\xe2\xa0\x81'
print(braille_char.encode('utf-8').hex())  # e2a081




print(chr(0x2801))  # ⠁
print(0x2801.to_bytes(3, "big"))  # b'\x28\x01'
bss = chr(0x2801).encode()


for b in bss:
    print(b)
    print(hex(b))

# n_ba = bytearray()
chs = []
ints = []
for char in chunks(chars, 8):
    code = 0x2800 | int.from_bytes(char, "big")
    chs.append(chr(code))
    ints.append(code)


c = [ch.encode() for ch in chs]
z = [i for i in ints]
bytearray(b"".join(i.to_bytes(8,"big") for i in ints), encoding="unicode_ignore")
# chars.decode(inv_braille_table)


# First char, first line:
ch_1_1 = (bits_1_8 >> 56) & 0b11000000
ch_1_2 = (bits_1_8 >> 48) & 0b00110000
ch_1_3 = (bits_1_8 >> 40) & 0b00001100
ch_1_4 = (bits_1_8 >> 32) & 0b00000011

print(format(ch_1_1, '08b'))  # 10000000
print(format(ch_1_2, '08b'))  # 00100000
print(format(ch_1_3, '08b'))  # 00000100
print(format(ch_1_4, '08b'))  # 00000001

ch_1 = ch_1_1 | ch_1_2 | ch_1_3 | ch_1_4
print(format(ch_1, '08b'))  # 10100101

# Generalize the above:

def get_char_from_bits_1_8(line, char):
    """
    Get the character at the given line and character position from the
    bits_1_8 string.
    """
    ch_1_1 = (bits_1_8 >> (56 - (line * 8 + char) * 2)) & 0b11000000
    ch_1_2 = (bits_1_8 >> (48 - (line * 8 + char) * 2)) & 0b00110000
    ch_1_3 = (bits_1_8 >> (40 - (line * 8 + char) * 2)) & 0b00001100
    ch_1_4 = (bits_1_8 >> (32 - (line * 8 + char) * 2)) & 0b00000011
    return ch_1_1 | ch_1_2 | ch_1_3 | ch_1_4

def p(x):
    print(format(x, '08b'))

ba = bitarray()
ba.frombytes(bits_1_8.to_bytes(8, 'big'))
for i in range(bits_1_8.bit_length() // 8):
    a = ba[:8] & bitarray("11000000")
    b = ba[8:16] & bitarray("00110000")
    c = ba[16:24] & bitarray("00001100")
    d = ba[24:32] & bitarray("00000011")
    total = a | b | c | d

    # The width is 8 characters, so 16 bits/2 bytes.
    # With slicing:
    ba_1 = ba[::1]
    ba_2 = ba[1::1]
    zipped = zip(ba_1, ba_2)
    c = list(zipped)[:4]

ba = bitarray()
ba.frombytes(bits_1_8.to_bytes(8, 'big'))
chs = []

w = 8
accs = [[], [], [], []]
for i, pair in enumerate(zip(ba[::8], ba[1::8])):
    accs[i % 4].append(pair)


print(accs)



print(format(get_char_from_bits_1_8(0, 0), '08b'))  # 10100101
print(format(get_char_from_bits_1_8(1, 0), '08b'))  # 01011010
print(format(get_char_from_bits_1_8(2, 0), '08b'))  # 11111111
print(format(get_char_from_bits_1_8(3, 0), '08b'))  # 00000000

def get_char_from_bits_1_8(line, char):
    """
    Get the character at the given line and character position from the
    bits_1_8 integer.
    """
    return bits_1_8 >> (line * 8 + char) * 2 & 0b11

print(format(get_char_from_bits_1_8(0, 0), "08b"))
print(format(get_char_from_bits_1_8(0, 1), "08b"))
print(format(get_char_from_bits_1_8(1, 1), "08b"))


# fmt: on

# 10  11
# 10  11
# 10  00
# 10  00


#
#
#
#


ba_2_2 = bitarray(f"{bits_2_2:b}")
ba_2_4 = bitarray(f"{bits_2_4:b}")

print(ba_2_2[2:4])
print(ba_2_2[10:12])
print(ba_2_2[18:20])
print(ba_2_2[26:28])

print(ba_2_4[2:4])
print(ba_2_4[10:12])
print(ba_2_4[18:20])
print(ba_2_4[26:28])

print(ba_2_4[34:36])
print(ba_2_4[42:44])
print(ba_2_4[50:52])
print(ba_2_4[58:60])

width_2_2 = 2
width_2_4 = 4
