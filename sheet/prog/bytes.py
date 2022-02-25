#!/usr/bin/env python3

from struct import pack, unpack

# immutable(変更不可能)なbytesと、mutable(変更可能)なbytearrayがある。
# ここではbytesarrayを主に説明する。

b1 = b"Hello"                   # bytes型
b2 = bytearray(b"Hello")        # bytearray型
# b"こんにちわ"                 # ASCII文字以外は不可
b3 = bytearray(b"\xDE\xAD\xBE\xEF")  # 16進数から
b4 = bytearray.fromhex("DEADBEEF")   # 16進数から
a = 9250
b5 = a.to_bytes(2, "big")       # intから(バイト数とエンディアン指定)
print(b3.hex())                 # 16進数へ
print(b3[1])                    # 173 ( = 0xDE)

b3.count(b"\xde\xad")           # 出現数を数える
b3.count(173)                   # 0-255の整数も指定できる

b1.decode("utf-8")       # bytes or bytearrayの内容を文字列として解釈した結果を返す
# b3.decode("utf-8")     # 指定したエンコーディングとして解釈できない時は[[ERROR]] UnicodeDecodeError
b3.decode("utf-8", errors="ignore")       # errors = "ignore" または "replace"を使用して回避

# struct: pack, unpack
# バイト列(バイナリデータ)の解釈
# C言語のAlignmentとパディングを理解せずに使用しないこと！
jpegheader = b"\xff\xd8\xff\xe0\x00\x10\x4a\x46\x49\x46\x00\x01\x01\x01\x00\xf0\x00\xf0"
(marker_soi, soi, marker_app0, app0, len_field, JFIF, verno, dpi_unit, width, height) = unpack(">BBBBH5sHBHH", jpegheader)
print(f"{width} x {height}")
pascalstr = pack("B5s", 5, b"Hello")

# byte order
# 文字 バイトオーダー サイズ アライメント
# @(省略時) ネイティブ ネイティブ ネイティブ
# = ネイティブ 標準 なし
# < リトルエンディアン 標準 なし
# > ビッグエンディアン 標準 なし
# ! ネットワーク (>と同じ)

# フォーマット Cの型 Pythonの型  サイズ(Standard時)
# x (パディング) 読み込まない 1
# c char bytes 1
# b/B singed/unsighed char  integer 1
# ? _Bool bool 1
# h/H signed/unsigned short integer 2
# i/I signed/unsigned int integer 4
# l/L signed/unsigned long integer **4**
# q/Q signed/unsigned long long integer 8
# n/N ssize_t/size_t integer (@のみ使用可)
# e なし(半精度浮動小数点) float 2
# f float float 4
# d double float 8
# s/p char[] bytes (5sなどで指定)
# P void * integer (@のみ使用可)
# hhhhは4hでも良い

# .startwith(), .endwith(), .find(), .index(), .join()なども使用できる。
# memoryviewを利用してバッファアクセスを行うことも出来る。
