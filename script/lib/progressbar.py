# -*- coding: utf-8 -*-
"""1行を書き換え続ける進捗表示。

受け持つのは「機構」だけ —— バーの描画、再描画スレッド、行の消去、通常の出力を
潰さずに結果行を挟む段取り、端末幅に応じた欄の配分。
「どの欄を、どんな文言で出すか」は仕事ごとに違うので、LiveLine を継承して
parts() で返す（必要なら cell_color() でバーの色も決める）。

標準ライブラリだけで書くこと（理由は termtext を参照）。

使い方:

    class MyProgress(LiveLine):
        def parts(self):
            return [f"{self.done}/{self.total}", BarSlot(self.ratio), f"{self.ratio:4.0%}"]

    with MyProgress(enabled=sys.stdout.isatty()) as progress:
        for item in items:
            ...
            progress.refresh()
            progress.report(f"done: {item}")
"""

from __future__ import annotations

import math
import shutil
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TextIO

from .termcolor import RGB, hue_rgb, scale_rgb, sgr, use_color_for
from .termtext import SGR_RESET, display_width, truncate_display

BAR_FILLED, BAR_EMPTY = "█", "░"
BAR_EMPTY_RGB = (80, 80, 80)

# 端数のマスを埋める部分ブロック（1/8〜7/8）。桁を増やさずに解像度が8倍になるので、
# 遅い仕事でもバーが常に動いて見える。全角ではないので1マス1桁のまま。
BAR_PARTIALS = "▏▎▍▌▋▊▉"

# バーの幅は端末の空きに合わせて伸縮させる。固定幅だと、狭い端末では枠だけで行の半分以上を
# 食って数字が消え（40桁なら56%）、広い端末では右に余白が残ったまま解像度も上がらない。
BAR_MIN_WIDTH, BAR_MAX_WIDTH = 8, 40

# アニメーションの再描画頻度。進捗の報告は間隔が空くことがある（ffmpegの -progress は
# 0.5秒に1回）ので、滑らかに動かすには独立したティックが要る。
# 15fpsあれば波の流れは十分見える。
PROGRESS_FPS = 15.0

# 単色のバーに流す光沢の既定値。
BAR_WAVE_SECONDS = 1.6    # 波が左から右へ1周する秒数
BAR_WAVES = 1.5           # バー内に見える波の数
BAR_WAVE_FLOOR = 0.55     # 波の谷での明度（1.0が元の色）

# レインボーの既定値。
RAINBOW_SECONDS = 2.0     # 色相が1周する秒数
RAINBOW_TURNS = 1.0       # バーの端から端で色相が何周するか

# バーの枠「[]」が食う桁数。
BAR_FRAME_WIDTH = 2

# 進捗行の既定色（cell_color を上書きしなかったとき）。
DEFAULT_BAR_RGB = (70, 145, 240)


@dataclass(frozen=True)
class BarSlot:
    """parts() の並びの中で、バーが入る場所を表す印。

    ratio は 0〜1 の進み具合。intensity は「どれくらい勢いがあるか」で、
    cell_color() が色を決めるのに使う（速度、スループット、負荷など）。
    色を使わない実装では無視してよい。
    """

    ratio: float
    intensity: float = 0.0


def wave_level(position: float, phase: float, waves: float = BAR_WAVES,
               seconds: float = BAR_WAVE_SECONDS, floor: float = BAR_WAVE_FLOOR) -> float:
    """光沢の明度（floor〜1.0）。position はバー内の位置(0〜1)、phase は経過秒。

    単色のバーでも、明度を波で揺らすと左から右へ流れて見える。
    """
    wave = math.sin(2 * math.pi * (position * waves - phase / seconds))
    return floor + (1 - floor) * (wave + 1) / 2


def rainbow_rgb(position: float, phase: float, turns: float = RAINBOW_TURNS,
                seconds: float = RAINBOW_SECONDS) -> RGB:
    """バー内を流れるレインボーの、その位置での色。"""
    return hue_rgb(position * turns - phase / seconds)


def bar_chars(ratio: float, width: int) -> list[str]:
    """バーのマスを並べる。満たない端数は部分ブロック（▏〜▉）で埋める。

    1マスを8段に割れるので、幅20でも0.625%刻みになり、5%刻みだった頃のような
    「しばらく動かない」が消える。
    """
    exact = max(ratio, 0.0) * width
    full = min(int(exact), width)
    eighths = int((exact - full) * 8)
    chars: list[str] = []
    for index in range(width):
        if index < full:
            chars.append(BAR_FILLED)
        elif index == full and eighths > 0:
            chars.append(BAR_PARTIALS[eighths - 1])
        else:
            chars.append(BAR_EMPTY)
    return chars


# render_bar に渡す色関数。バー内の位置(0〜1)を受け取って色を返す。
CellColor = Callable[[float], RGB]


def render_bar(ratio: float, width: int, cell_color: CellColor | None = None) -> str:
    """「[███▌░░░]」を組み立てる。cell_color を渡すとマスごとに着色する。

    cell_color は (位置0〜1) -> RGB。同じ色が続くところではSGRを繰り返さないので、
    幅40でも行が無駄に長くならない。
    """
    chars = bar_chars(ratio, width)
    if cell_color is None:
        return f"[{''.join(chars)}]"
    cells: list[str] = []
    last: RGB | None = None
    for index, char in enumerate(chars):
        rgb = BAR_EMPTY_RGB if char == BAR_EMPTY else cell_color(index / max(width - 1, 1))
        if rgb != last:   # 同じ色が続くならSGRを繰り返さない
            cells.append(sgr(rgb))
            last = rgb
        cells.append(char)
    return f"[{''.join(cells)}{SGR_RESET}]"


class LiveLine:
    """端末の最終行を書き換え続ける表示。

    -j で並列にしても行が混ざらないよう、仕事ごとではなく全体を1行だけ書き換える。
    端末以外（パイプ・cron）では enabled=False にすれば何もしないので、
    ログの見た目は素のままになる。

    継承して parts() を実装する。状態を触るときは self.lock を取ること
    （再描画スレッドが同じ状態を読むため）。RLockなので、ロックを持ったまま
    refresh() や report() を呼んでも固まらない。
    """

    def __init__(self, enabled: bool, stream: TextIO | None = None,
                 fps: float = PROGRESS_FPS, animate: bool | None = None) -> None:
        self.stream = stream or sys.stdout
        self.enabled = enabled
        self.color = enabled and use_color_for(self.stream)
        # 色を使わないなら波は見えないので、既定ではティックを回さない
        self.animate = self.color if animate is None else animate
        self.fps = fps
        self.lock = threading.RLock()
        self.started = time.monotonic()
        # バー以外の欄に割り当てた桁数（この実行で見た最大）と、そのときの端末幅
        self.fixed_columns = 0
        self.last_columns = 0
        self._stop = threading.Event()
        self._ticker: threading.Thread | None = None

    # -- 呼ぶ側が実装する ---------------------------------------------------

    def parts(self) -> list[str | BarSlot]:
        """1行に並べる欄。バーを入れたい場所に BarSlot を置く。

        self.lock を持った状態で呼ばれる。表示のために状態を進めてもよい。
        """
        raise NotImplementedError

    def cell_color(self, slot: BarSlot, position: float, phase: float) -> RGB:
        """バー1マスの色。position はバー内の位置(0〜1)、phase は経過秒。

        既定は単色に光沢を流すだけ。速度で色を変えたいなら上書きする。
        """
        return scale_rgb(DEFAULT_BAR_RGB, wave_level(position, phase))

    # -- 機構 ---------------------------------------------------------------

    def __enter__(self) -> "LiveLine":
        """アニメーション用の再描画スレッドを回し始める。"""
        if self.animate:
            self._ticker = threading.Thread(target=self._tick, daemon=True)
            self._ticker.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _tick(self) -> None:
        while not self._stop.wait(1.0 / self.fps):
            self.refresh()

    def refresh(self) -> None:
        """今の状態で描き直す。"""
        with self.lock:
            self._render()

    def report(self, line: str, error: bool = False) -> None:
        """結果行を1本出す。進捗行を潰さないように、消す→出す→描き直す。"""
        with self.lock:
            self._erase()
            print(line, file=sys.stderr if error else self.stream, flush=True)
            self._render()

    def close(self) -> None:
        """進捗行を消して、以降は普通の出力に戻す。"""
        # 先にティックを止める。ロックを持ったまま join すると、_render 待ちの
        # スレッドと相討ちになって固まる。
        self._stop.set()
        if self._ticker is not None:
            self._ticker.join(timeout=1.0)
            self._ticker = None
        with self.lock:
            self._erase()
            self.enabled = False

    def _erase(self) -> None:
        if self.enabled:
            print("\r\033[K", end="", file=self.stream, flush=True)

    def _render(self) -> None:
        if not self.enabled:
            return
        phase = time.monotonic() - self.started
        columns = shutil.get_terminal_size(fallback=(80, 24)).columns
        line = self._compose(self.parts(), phase, columns)
        print("\r\033[K" + truncate_display(line, columns - 1),
              end="", file=self.stream, flush=True)

    def _compose(self, parts: list[str | BarSlot], phase: float, columns: int) -> str:
        """バー以外の欄を先に測り、余った桁をバーに与えて1行にする。

        欄はその時々で出たり消えたりする（仕事の合間は速度も残り時間も名前も無い）。
        そのつど測って割り当てると、欄が戻るたびにバーが縮んで幅が踊るので、この実行で
        見た最大の桁数で確保する。端末幅が変わったら測り直す。
        """
        fixed = sum(display_width(p) for p in parts if isinstance(p, str)) + len(parts) - 1
        if columns != self.last_columns:
            self.last_columns, self.fixed_columns = columns, 0
        self.fixed_columns = max(self.fixed_columns, fixed)
        room = columns - 1 - self.fixed_columns - BAR_FRAME_WIDTH
        width = max(BAR_MIN_WIDTH, min(BAR_MAX_WIDTH, room))
        return " ".join(
            self._draw(part, phase, width) if isinstance(part, BarSlot) else part
            for part in parts)

    def _draw(self, slot: BarSlot, phase: float, width: int) -> str:
        if not self.color:
            return render_bar(slot.ratio, width)
        return render_bar(slot.ratio, width,
                          lambda position: self.cell_color(slot, position, phase))
