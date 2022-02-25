#!/usr/bin/env python3

import re

# r""で、\をそのまま使用できる
pattern = r"([\w+\.]+)@(\w+\.[\w]+)"
content = "kcrt@kcrt.net"

# POSIXキャラクタクラス([:alpha:]など)は使用できない

ret = re.match(pattern, content)
if ret:
    print(ret.group(0))  # kcrt@kcrt.net
    print(ret.group(1))  # kcrt
else:
    print("No match!")


# 名前付きキャプチャ: (?P<name>...)
ret = re.match(r"(?P<hour>\d\d):(?P<min>\d\d)", "12:34")
ret.group("hour")   # => 12

# オプションは
re.match(pattern, content, re.IGNORECASE)
#  re.ASCII (re.A)      ASCIIモード(ないとアラビア数字以外も\dでマッチ)
#  re.LOCALE (re.L)     ローカル言語モード (非推奨)
#  re.UNICODE (re.U)    Unicodeモード (指定不要)
#  re.IGNORECASE (re.I) 大文字小文字無視
#  re.MULTILINE (re.M)  複数行
#  re.DEBUG, re.VERBOSE(re.X)

# 事前にコンパイルしておくことで再利用･高速化できる
# 上記オプションも指定可能
pat = re.compile(pattern, re.ASCII)
pat.match(content)

# 全体一致でなくても良い時
re.search(pattern, content)

# マッチした物をすべて探す(リスト・イテレータ)
re.findall(pattern, content)
re.finditer(pattern, content)


# 置き換え
re.sub("world", "xxxxx", "Hello, world.")
# => Hello, xxxxx
re.sub("world", r"*\g<0>*", "Hello, world.")
# => Hello, *world*
# 対応グループは\1 (== \g<1>)という表記もできる
# \0は使用できないので\g<0>を使用すること
