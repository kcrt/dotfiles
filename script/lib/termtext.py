# -*- coding: utf-8 -*-
"""端末に文字を並べるときの幅の勘定。

日本語を含む行を桁揃えすると len() では合わない。全角は2桁を食うし、色指定
（SGR）は1桁も食わない。その2つを踏まえて数える・詰める・切るためのもの。

標準ライブラリだけで書くこと。PEP 723 の dependencies は呼ぶ側のスクリプトに
しか書けないので、ここで外部パッケージに依存すると import する全スクリプトが
同じ依存を書き並べる羽目になる。
"""

from __future__ import annotations

import re
import unicodedata

# SGR（色指定）。表示幅を持たないので、幅を数えるときは取り除く。
SGR_PATTERN = re.compile(r"\x1b\[[0-9;]*m")

# 色を既定へ戻す。色の途中で切り詰めたときに足す。
# termcolor 側の綴りもこれを使う（termcolor -> termtext の一方向に保つため、
# 逆向きの import をしなくて済むようこちらに置いてある）。
SGR_RESET = "\033[0m"

# 切り詰めたことを示す記号。1桁分の幅を取る。
ELLIPSIS = "…"


def char_width(ch: str) -> int:
    """端末上での1文字の表示幅。

    結合文字（濁点など）は前の文字に乗るので0桁。macOSのファイル名はNFDなので
    「が」が「か」+ 結合濁点の2コードポイントで届く。これを1文字2桁と数えると
    日本語のファイル名だけ幅が余計に見積もられ、桁揃えが崩れる。

    全角（W/F）は2桁。曖昧幅（A: 罫線・★・ブロック文字）は、端末の既定設定に
    合わせて1桁として扱う。
    """
    if unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in "WF" else 1


def display_width(text: str) -> int:
    """端末上での表示幅。日本語などの全角文字は2桁として数える。

    色指定（SGR）は桁を食わないので、数える前に取り除く。
    """
    return sum(char_width(ch) for ch in SGR_PATTERN.sub("", text))


def strip_sgr(text: str) -> str:
    """色指定を取り除いた素の文字列。ログやファイルへ落とすときに使う。"""
    return SGR_PATTERN.sub("", text)


def pad_display(text: str, width: int) -> str:
    """表示幅が width になるよう右を空白で埋める。既に超えていればそのまま返す。"""
    return text + " " * max(width - display_width(text), 0)


def truncate_display(text: str, limit: int) -> str:
    """表示幅が limit を超えないよう末尾を落とす。進捗行の折り返しを防ぐため。

    色指定（SGR）は桁を食わないのでそのまま通す。色の途中で切れても端末に色が
    残らないよう、切り詰めたときはリセットを足す。
    """
    if display_width(text) <= limit:
        return text
    kept: list[str] = []
    width, index = 0, 0
    while index < len(text):
        match = SGR_PATTERN.match(text, index)
        if match:
            kept.append(match.group())
            index = match.end()
            continue
        width += char_width(text[index])
        if width > limit - 1:
            break
        kept.append(text[index])
        index += 1
    tail = SGR_RESET if SGR_PATTERN.search(text) else ""
    return "".join(kept) + ELLIPSIS + tail


def clip_display(text: str, width: int) -> tuple[str, int]:
    """表示幅が width に収まるよう切る。全角文字を半分で割らない。

    切った文字列と、その実際の表示幅を返す（幅は呼ぶ側が余白を詰めるのに使う。
    全角の手前で切ると width より1桁狭くなることがあるため、数え直さずに済む）。
    truncate_display と違って「…」は足さない。TUIの欄のように、切れたことより
    桁が合っていることが大事な場所で使う。
    """
    used = 0
    for index, ch in enumerate(text):
        w = char_width(ch)
        if used + w > width:
            return text[:index], used
        used += w
    return text, used


def fit_display(text: str, width: int, align: str = "<") -> str:
    """表示幅をちょうど width にする。長ければ切り、短ければ空白で埋める。

    欄の幅が決まっている表で使う。切るか詰めるかを呼ぶ側で分岐しなくて済む。
    align=">" で右詰め。
    """
    width = max(0, width)
    body, used = clip_display(text, width)
    padding = " " * (width - used)
    return padding + body if align == ">" else body + padding
