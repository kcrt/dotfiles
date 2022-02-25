#!/usr/bin/env python3

numFruits = 30
fruits = "apple"

# クラシカルな方法 %演算子を使用する (Python 2系でも使用できる)
"I have %d %ss." % (numFruits, fruits)  # => I have 30 apples.
"I have %(a)d %(b)ss" % {"a": numFruits, "b": fruits}

# format関数を使用する
format(numFruits, "05d")  # => 00030

# 文字列のformatメソッドを使用する
"I have {} {}s".format(numFruits, fruits)
"I have {0} {1}s".format(numFruits, fruits)
"I have {a} {b}s".format(a=numFruits, b=fruits)
"{num:05d}".format(num=numFruits)   # :以降で書式指定も指定できる

# f文字列 (3.6以降) - 今後主流になります(たぶん)
f"I have {numFruits} and {fruits}"  # 変数を使用できる！
f"{numFruits:05d}"   # 書式指定も出来る
f"{numFruits * 10}"  # => 300, 式まで使用できる！！

# 書式指定ミニ言語仕様
# https://docs.python.org/ja/3.7/library/string.html#formatspec

# align sign # 0 width grouping .precision type

price = 12312.3
print(f"{price:#^+19,.3f}")  # => ####+12,312.300####

# align:
# <: 左詰, >: 右詰, =: 符号があるときのみ, ^: 中央詰め
# オプションで何で埋めるかを指定できる(上記の#^)
# sign:
# +: 正でも負でも符号, -: 負のみ符号, スペース: 正の場合はスペース・負は符号
# width:
# 最小のフィールド幅
# grouping_option:
# _と,: _区切り または カンマ区切り
# .precision:
# 浮動小数点の小数点下の桁数
# type:
# --- 文字列型 ---
# s - 文字列 (省略時)
# --- 整数 ---
# b - 2進数
# c - 数値に対応するUnicode文字
# d - 10進数 (省略時)
# o - 8進数
# x/X - 16進数(小文字/大文字)
# n - 数値(ロケールに従う)
# --- 浮動小数点 ---
# e/E - 指数表記
# f/F - 固定小数点表記
# g/G - e/f/E/Fなどを自動で選ぶ (省略時)
# n - 数値(ロケールに従う)
# % - 100倍してパーセントをつける
