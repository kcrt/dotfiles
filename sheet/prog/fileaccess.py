#!/usr/bin/env python3

from struct import unpack

fp = open("/data/hello.txt", "r", encoding="utf-8", errors='ignore', newline=None)
# ファイル名以外は省略可
# mode:
#   r - 読み込み専用 (省力可)
#   w - 書き込み (既存の内容は削除)
#   x - 書き込み、すでにあるとエラー
#   a - 追記
#   b - バイナリ
#   t - テキスト (省略可)
#   + - 更新 (読み書き)
# buffering=0 (テキスト読み込み時は使用不可)
# errors (en/decodeできないときにどうするか):
#   strict(省略時): ValueError例外
#   ignore: 無視する
#   replace: '?'などに置換
#   他に surrogateescape, xmlcharrefreplace, backslashreplace, namereplaceなど
# newline (改行コード):
#   None(省略時): '\n'を環境に合わせる
#   '\n', '\r', '\r\n'

fp.read()   # ファイル内容をすべて読み込む
fp.seek(0)  # 最初から
fp.readline()   # 1行読み込み
fp.read(4)  # 4**文字**読み込み (bではbyte)
fp.tell()   # => バイト位置

fp.seek(0)
# 1行づつ処理
for myline in fp:
    # mylineは改行コード付きなのに注意
    print(myline.rstrip())

fp.close()  # 閉じる


# ほとんどの場合はwithを使うことが良い
with open("/data/hello.txt", "w") as fp:
    # 改行コードは自分でつける
    fp.write("こんにちわ\n")
    fp.write("Hello, world\n")
# withが終われば自動的にclose


with open("/data/apple.jpg", "r+b") as fp:
    # w+bだと、既存の内容はすべて消える
    data = fp.read(2)
    print(data)  # => b'\xff\xd8'
    # バイナリはpack, unpackと組み合わせると便利 (bytes参照)
    data = fp.read(16)
    info = unpack(">bbH5sHbHH", data)
    print(f"Image size: {info[6]} x {info[7]}")


# 低レベル処理のos.open, os.readなどを使用することも出来るが通常はおすすめしない。
