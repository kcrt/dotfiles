# -*- coding: utf-8 -*-
"""バイト数と秒数を人が読める形にする。

変換前後を並べて見せる用途（元 → 先 と削減率）まで面倒を見る。桁が縦に揃うよう
幅を固定する align 付きの書式もここにある。

標準ライブラリだけで書くこと（理由は termtext を参照）。
"""

from __future__ import annotations

from .termcolor import RGB, paint

SIZE_UNITS = ("B", "KB", "MB", "GB", "TB", "PB")

# サイズの数字に割り当てる桁数。単位は大きい方の値に合わせるので、どの値も1024未満に
# 収まり、"1023.9" の6桁が上限になる。
SIZE_NUMBER_WIDTH = 6

# 変換して元より太ったことを示す色。オレンジ。
GREW_RGB = (220, 130, 30)


def size_unit(n: float) -> str:
    """そのバイト数を読みやすく表せる単位。"""
    for unit in SIZE_UNITS[:-1]:
        if abs(n) < 1024:
            return unit
        n /= 1024
    return SIZE_UNITS[-1]


def common_unit(*sizes: float) -> str:
    """複数のサイズを並べて見せるときに共通で使う単位。

    大きい方に合わせる。小さい方に合わせると、比が開いたときに大きい側が
    「26774.3 KB」のように桁あふれして列が崩れるため。小さい側の桁は human() が
    小数を増やして残す。
    """
    return size_unit(max(sizes))


def human(n: float, unit: str | None = None, align: bool = False,
          sep: str = " ") -> str:
    """バイト数を読める単位にする。

    unitを渡すとその単位で表す。変換前後を並べるときに単位が食い違うと
    「1.0 MB → 194.0 KB」のように増えたと錯覚するので、左右で揃えるために使う
    （揃える単位は common_unit で決める）。
    align=True では数字を右詰め・単位を左詰めにして幅を固定し、結果行のように縦に
    並べたとき桁が揃うようにする（このとき sep は使わない）。
    sep="" で「1.5MB」の形。外側で右詰めする欄に入れるときに使う。
    """
    unit = unit or size_unit(n)
    value = n / 1024 ** SIZE_UNITS.index(unit)
    # 1未満は桁数を増やす。大きい方に単位を合わせると小さい方が「0.9 MB」のように
    # 潰れるので、有効数字を2桁保つ。どちらも幅は同じなので列は揃ったまま
    decimals = 2 if 0 < abs(value) < 1 else 1
    return (f"{value:{SIZE_NUMBER_WIDTH}.{decimals}f} {unit:<2}" if align
            else f"{value:.{decimals}f}{sep}{unit}")


def size_change(src_size: int, dst_size: int, show_saved: bool = False,
                grew_rgb: RGB = GREW_RGB) -> str:
    """「  1.3 MB →  800.0 KB ( 60%)」の形。単位は左右で揃える。

    結果行と合計行で同じ欄・同じ幅を使うため、整形はここ1箇所にまとめる。
    show_saved=True では括弧の中に増減量も添える（合計行用）。

    変換して元より太った場合は「増加」と書き、括弧ごと着色する。
    負の削減量（-113.3 MB 削減）は読み取りに一拍かかるうえ、見逃しやすいため。
    """
    unit = common_unit(src_size, dst_size)
    ratio = dst_size / src_size if src_size else 0
    delta = src_size - dst_size
    note = ""
    if show_saved:
        note = (f", {human(delta, unit)} 削減" if delta >= 0
                else f", {human(-delta, unit)} 増加")
    change = f"({ratio:>4.0%}{note})"
    if delta < 0:
        change = paint(change, grew_rgb)
    return (f"{human(src_size, unit, align=True)} → {human(dst_size, unit, align=True)} "
            f"{change}")


def clock(seconds: float) -> str:
    """秒を 1:02:03 / 2:03 形式にする。"""
    total = int(max(seconds, 0))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"
