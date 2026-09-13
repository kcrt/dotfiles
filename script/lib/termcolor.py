# -*- coding: utf-8 -*-
"""端末での着色。24bit色（truecolor）と256色の両方。

出力先が端末かどうかを見て、色を出してよいときだけ着色する。パイプやファイルへ
流すときは色を落とすので、呼ぶ側が分岐を書かなくてよい。

24bitと256色を分けてあるのは、出せる条件が違うため。256色はほぼどの端末でも
出せるが、24bitは COLORTERM を見ないと分からない。`--color` を持つスクリプトは
set_color_mode() で判定ごと上書きできる。

標準ライブラリだけで書くこと（理由は termtext を参照）。
"""

from __future__ import annotations

import colorsys
import os
import sys
from typing import TextIO

from .termtext import SGR_RESET, pad_display

RGB = tuple[int, int, int]

# 行頭の状態マーカー（NG / skip / 注意）に割り当てる既定の表示幅。
MARKER_WIDTH = 7

# --color always/never による上書き。None は自動判定。
_FORCED: bool | None = None


def set_color_mode(mode: str) -> None:
    """`--color auto|always|never` を解釈して、以降の判定を固定する。

    always は端末以外へ出すときも色を付ける（less -R やファイルへ残す用）。
    """
    global _FORCED
    try:
        _FORCED = {"always": True, "never": False, "auto": None}[mode]
    except KeyError:
        raise ValueError(f"色の指定が不正です: {mode!r}（auto/always/never）") from None


def color_enabled(stream: TextIO | None = None) -> bool:
    """その出力先に色（256色まで）を出してよいか。

    NO_COLOR（https://no-color.org/）と TERM=dumb は尊重する。
    パイプやファイルへ流すときは、色が中身に混ざらないよう落とす。
    """
    if _FORCED is not None:
        return _FORCED
    stream = stream or sys.stdout
    if os.environ.get("NO_COLOR") or os.environ.get("TERM") == "dumb":
        return False
    return stream.isatty()


def use_color_for(stream: TextIO) -> bool:
    """その出力先に24bit色を出してよいか。

    サブパラメータのコロン区切り（38:2::r:g:b）はTerminal.appが解釈しないので、
    綴りは必ずセミコロン区切りにすること。判定は COLORTERM のみを見る保守的な
    もので、分からなければ色を使わず素の見た目に落とす。

    stdoutとstderrは別々に判定する。エラー行はstderrへ出るので、stdoutだけを
    見ると `cmd 2> err.log` でログにエスケープが混ざる。
    """
    if not color_enabled(stream):
        return False
    if _FORCED:
        return True        # --color always は24bitも出す指示とみなす
    return os.environ.get("COLORTERM", "").lower() in ("truecolor", "24bit")


def use_color() -> bool:
    """stdout に24bit色を出してよいか。"""
    return use_color_for(sys.stdout)


def sgr(rgb: RGB) -> str:
    """前景色を指定するエスケープ列（24bit）。"""
    return f"\033[38;2;{rgb[0]};{rgb[1]};{rgb[2]}m"


def sgr256(code: int) -> str:
    """前景色を指定するエスケープ列（256色パレットの番号）。"""
    return f"\033[38;5;{code}m"


def paint(text: str, rgb: RGB, stream: TextIO | None = None) -> str:
    """24bit色が使える端末なら着色する。使えないならそのまま返す。"""
    return (f"{sgr(rgb)}{text}{SGR_RESET}"
            if use_color_for(stream or sys.stdout) else text)


def paint256(text: str, code: int, stream: TextIO | None = None) -> str:
    """256色パレットで着色する。色が使えないならそのまま返す。"""
    return (f"{sgr256(code)}{text}{SGR_RESET}"
            if color_enabled(stream) else text)


def hue_rgb(hue: float, saturation: float = 0.85, value: float = 1.0) -> RGB:
    """色相環の位置（0〜1、範囲外は巻き戻す）から RGB を作る。"""
    r, g, b = colorsys.hsv_to_rgb(hue % 1.0, saturation, value)
    return (round(r * 255), round(g * 255), round(b * 255))


def scale_rgb(rgb: RGB, level: float) -> RGB:
    """明度を level 倍にする（1.0で元の色）。255は超えない。"""
    return (min(255, round(rgb[0] * level)),
            min(255, round(rgb[1] * level)),
            min(255, round(rgb[2] * level)))


def status_line(marker: str, rgb: RGB | None, text: str,
                stream: TextIO | None = None, width: int = MARKER_WIDTH) -> str:
    """「  NG     名前: 理由」の形。マーカーだけ色を付ける。

    桁揃えは display_width（色指定を除いて数える）に任せるので、
    色の有無で欄がずれることはない。
    """
    painted = paint(marker, rgb, stream) if rgb else marker
    return f"  {pad_display(painted, width)}{text}"
