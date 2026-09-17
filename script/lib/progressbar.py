# -*- coding: utf-8 -*-
"""A single terminal line, rewritten in place, for showing progress.

It owns the mechanism only: drawing the bar, the redraw thread, erasing the line,
the dance that lets ordinary output through without clobbering the progress line,
and dividing the terminal width between the fields.
"Which fields, and in what wording" differs per job, so a subclass of LiveLine
returns them from parts() (and may decide the bar's color in cell_color()).

Use the standard library only (see termtext for why).

Usage:

    class MyProgress(LiveLine):
        def parts(self):
            return [f"{self.done}/{self.total}", BarSlot(self.ratio), f"{self.ratio:4.0%}"]

    with MyProgress(enabled=sys.stderr.isatty()) as progress:
        for item in items:
            ...
            progress.refresh()
            progress.report(f"done: {item}")

ProgressBar is that subclass already written, for when the usual count / bar /
percent / rate / time-left is what the job wants:

    for item in ProgressBar(items, desc="変換"):
        ...
"""

from __future__ import annotations

import math
import shutil
import sys
import threading
import time
from collections.abc import Callable, Iterable, Iterator, Sized
from dataclasses import dataclass
from typing import Self, TextIO

from .humanize import clock, common_unit, human
from .termcolor import RGB, hue_rgb, scale_rgb, sgr, use_color_for
from .termtext import SGR_RESET, display_width, truncate_display

BAR_FILLED, BAR_EMPTY = "█", "░"
BAR_EMPTY_RGB = (80, 80, 80)

# Partial blocks (1/8 to 7/8) filling the fractional cell. Eight times the
# resolution at no extra width, so even a slow job keeps the bar visibly moving.
# These are not full-width, so a cell still costs one column.
BAR_PARTIALS = "▏▎▍▌▋▊▉"

# The bar stretches to whatever width is left over. A fixed width eats more than half
# the line on a narrow terminal (56% at 80 columns) and pushes the numbers out, while on
# a wide one it leaves empty space on the right without gaining any resolution.
BAR_MIN_WIDTH, BAR_MAX_WIDTH = 8, 40

# Redraw rate for the animation. Progress reports can arrive with gaps (ffmpeg's
# -progress fires twice a second), so a smooth animation needs an independent tick.
# 15fps is plenty to see the wave travel.
PROGRESS_FPS = 15.0

# Defaults for the sheen travelling along a single-color bar.
BAR_WAVE_SECONDS = 1.6    # seconds for one wave to cross from left to right
BAR_WAVES = 1.5           # waves visible within the bar at once
BAR_WAVE_FLOOR = 0.55     # brightness at the trough of the wave (1.0 is the base color)

# Defaults for the rainbow.
RAINBOW_SECONDS = 2.0     # seconds for the hue to go once around
RAINBOW_TURNS = 1.0       # times the hue goes around between the ends of the bar

# Columns taken by the bar's "[]" frame.
BAR_FRAME_WIDTH = 2

# Default color of the progress line (when cell_color is not overridden).
DEFAULT_BAR_RGB = (70, 145, 240)


@dataclass(frozen=True)
class BarSlot:
    """Marker for where the bar goes within the sequence returned by parts().

    `ratio` is the progress, 0-1. `intensity` is "how much is going on" - speed,
    throughput, load - for cell_color() to pick a color from. Implementations that
    do not use color can ignore it.
    """

    ratio: float
    intensity: float = 0.0


def wave_level(position: float, phase: float, waves: float = BAR_WAVES,
               seconds: float = BAR_WAVE_SECONDS, floor: float = BAR_WAVE_FLOOR) -> float:
    """Brightness of the sheen (floor to 1.0).

    `position` is 0-1 within the bar, `phase` is the elapsed seconds.

    Even a single-color bar appears to flow left to right once its brightness is
    modulated by a wave.
    """
    wave = math.sin(2 * math.pi * (position * waves - phase / seconds))
    return floor + (1 - floor) * (wave + 1) / 2


def rainbow_rgb(position: float, phase: float, turns: float = RAINBOW_TURNS,
                seconds: float = RAINBOW_SECONDS) -> RGB:
    """Color at this position of the rainbow flowing along the bar."""
    return hue_rgb(position * turns - phase / seconds)


def bar_chars(ratio: float, width: int) -> list[str]:
    """Lay out the bar's cells, filling the fractional remainder with a partial block (▏-▉).

    A cell splits into eight steps, so even at width 20 the step is 0.625%, and the
    "nothing moves for a while" of the old 5% steps is gone.
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


# Color function passed to render_bar: the position within the bar (0-1) -> a color.
CellColor = Callable[[float], RGB]


def render_bar(ratio: float, width: int, cell_color: CellColor | None = None) -> str:
    """Assemble "[███▌░░░]". Passing cell_color colors each cell.

    cell_color is (position 0-1) -> RGB. An SGR is not repeated while the color
    stays the same, so the line does not grow needlessly long even at width 40.
    """
    chars = bar_chars(ratio, width)
    if cell_color is None:
        return f"[{''.join(chars)}]"
    cells: list[str] = []
    last: RGB | None = None
    for index, char in enumerate(chars):
        rgb = BAR_EMPTY_RGB if char == BAR_EMPTY else cell_color(index / max(width - 1, 1))
        if rgb != last:   # do not repeat the SGR while the color is unchanged
            cells.append(sgr(rgb))
            last = rgb
        cells.append(char)
    return f"[{''.join(cells)}{SGR_RESET}]"


class LiveLine:
    """A display that keeps rewriting the last line of the terminal.

    One line is rewritten for the whole run rather than one per job, so lines do
    not interleave under -j. Where there is no terminal (a pipe, cron), pass
    enabled=False and nothing is drawn, leaving the log in its plain form.

    Subclass it and implement parts(). Hold self.lock while touching state (the
    redraw thread reads the same state). It is an RLock, so calling refresh() or
    report() while already holding it will not deadlock.

    The line goes to stderr, and so does everything a script says about its own
    progress. stdout is left for whatever the script is there to produce, so that
    `cmd > out` keeps showing the bar and `cmd | other` is not fed the commentary.
    The bar and the log have to share one stream in any case: a plain print() does
    not go through report(), so from the other stream it would walk over the line.
    """

    def __init__(self, enabled: bool, stream: TextIO | None = None,
                 fps: float = PROGRESS_FPS, animate: bool | None = None) -> None:
        self.stream = stream or sys.stderr
        self.enabled = enabled
        self.color = enabled and use_color_for(self.stream)
        # Without color the wave is invisible, so by default do not run the tick
        self.animate = self.color if animate is None else animate
        self.fps = fps
        self.lock = threading.RLock()
        self.started = time.monotonic()
        # Columns given to the fields other than the bar (the largest seen this run),
        # and the terminal width they were measured at
        self.fixed_columns = 0
        self.last_columns = 0
        self._stop = threading.Event()
        self._ticker: threading.Thread | None = None

    # -- implemented by the caller ------------------------------------------

    def parts(self) -> list[str | BarSlot]:
        """The fields to lay out on the line. Put a BarSlot where the bar belongs.

        Called with self.lock held. Advancing state for display purposes is fine.
        """
        raise NotImplementedError

    def cell_color(self, slot: BarSlot, position: float, phase: float) -> RGB:
        """Color of one cell of the bar.

        `position` is 0-1 within the bar, `phase` is the elapsed seconds.

        The default only runs a sheen over a single color. Override it to vary the
        color by speed.
        """
        return scale_rgb(DEFAULT_BAR_RGB, wave_level(position, phase))

    # -- mechanism ----------------------------------------------------------

    def __enter__(self) -> Self:
        """Start the redraw thread that drives the animation."""
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
        """Redraw with the current state."""
        with self.lock:
            self._render()

    def report(self, line: str, error: bool = False) -> None:
        """Emit one result line: erase, print, redraw, so the progress line survives."""
        with self.lock:
            self._erase()
            print(line, file=sys.stderr if error else self.stream, flush=True)
            self._render()

    def close(self) -> None:
        """Erase the progress line and go back to ordinary output."""
        # Stop the tick first. Joining while holding the lock deadlocks against the
        # thread waiting to enter _render.
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
        """Measure every field but the bar, then give the bar what is left.

        Fields come and go as the run proceeds (between jobs there is no speed, no ETA
        and no name). Measuring and dividing each time would shrink the bar whenever a
        field returned, making the width jitter, so reserve the largest count of columns
        seen this run. Re-measure when the terminal width changes.
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


# -- a ready-made line, for when the fields do not need deciding -------------

# Unit for "one item", the thing being counted when the caller does not say.
DEFAULT_UNIT = "it"

# Label in front of the time left. Japanese, like the rest of the user-visible
# wording in lib; a caller whose output is English passes eta_label="ETA".
ETA_LABEL = "残り"


class ProgressBar[T](LiveLine):
    """The usual fields, wrapped up: description, count, bar, percent, rate, time left.

    LiveLine asks for a subclass because the fields differ per job, but a lot of
    jobs want the same ones. This is that subclass, with a surface shaped like
    tqdm's - wrap the iterable and the counting happens on its own:

        for path in ProgressBar(paths, desc="変換"):
            convert(path)

    Counting by hand, for when the unit is not "one item":

        with ProgressBar(total=size, unit="B", desc="取得") as bar:
            for chunk in chunks:
                out.write(chunk)
                bar.update(len(chunk))

    report() is what tqdm calls write(): a line goes out and the bar survives it.
    Nothing here is required - where the wording matters, subclass LiveLine and
    write parts(), which is the whole point of it.

    `total` is taken from len(iterable) when it has one. Without a total there is
    no bar (nothing would fill it), so the line falls back to the count and rate.
    """

    def __init__(self, iterable: Iterable[T] | None = None, total: int | None = None,
                 desc: str = "", unit: str = DEFAULT_UNIT, enabled: bool | None = None,
                 stream: TextIO | None = None, eta_label: str = ETA_LABEL,
                 fps: float = PROGRESS_FPS, animate: bool | None = None) -> None:
        stream = stream or sys.stderr
        if total is None and isinstance(iterable, Sized):
            total = len(iterable)
        # Every caller of LiveLine ends up writing the same test, so make it the
        # default: draw nothing where the line cannot be rewritten (a pipe, cron).
        super().__init__(enabled=stream.isatty() if enabled is None else enabled,
                         stream=stream, fps=fps, animate=animate)
        self.iterable = iterable
        self.total = total
        self.desc = desc
        self.unit = unit
        self.eta_label = eta_label
        self.done = 0
        self.digits = len(str(total)) if total else 0
        self._entered = False

    # -- driving it ---------------------------------------------------------

    def update(self, n: int = 1) -> None:
        """Count n more units and redraw."""
        with self.lock:
            self.done += n
            self.refresh()

    def set_description(self, desc: str) -> None:
        """Change the leading field mid-run (the stage, the file being worked on)."""
        with self.lock:
            self.desc = desc
            self.refresh()

    def __enter__(self) -> Self:
        self._entered = True
        return super().__enter__()

    def __iter__(self) -> Iterator[T]:
        """Yield the wrapped iterable, counting one unit per item.

        Outside a `with`, the loop owns the line and erases it on the way out -
        including when the loop is left early, since closing the generator runs
        the `with` on the way. Inside one, the `with` already owns it.
        """
        if self.iterable is None:
            raise TypeError("ProgressBar has no iterable to walk; count with update()")
        if self._entered:
            yield from self._counted(self.iterable)
        else:
            with self:
                yield from self._counted(self.iterable)

    def _counted(self, iterable: Iterable[T]) -> Iterator[T]:
        for item in iterable:
            yield item
            self.update()

    # -- what it shows ------------------------------------------------------

    @property
    def ratio(self) -> float:
        """Progress 0-1. Past the total (a wrong estimate) the bar stays full."""
        return min(self.done / self.total, 1.0) if self.total else 0.0

    @property
    def rate(self) -> float:
        """Units per second since the start (0 before the clock has moved)."""
        elapsed = time.monotonic() - self.started
        return self.done / elapsed if elapsed > 0 else 0.0

    def amount(self, n: float, decimals: int = 0, size_unit: str | None = None) -> str:
        """Render a count of the unit. Bytes read better as KB/MB than as digits.

        `size_unit` forces the unit, so that the two sides of "96.0MB/300.0MB" are
        not picked apart from each other (the reason humanize has common_unit).
        """
        if self.unit == "B":
            return human(n, size_unit, sep="")
        # A decimal place is noise once the number is big enough to not need it,
        # and a rate can run to four digits ("1688.6it/s" says nothing "1689it/s"
        # does not), so drop it there rather than let the field jitter wider.
        return f"{n:.{decimals if abs(n) < 100 else 0}f}{self.unit}"

    def counter(self) -> str:
        """The "done of total" field, in whichever form the unit reads best."""
        if self.unit != "B":
            return f"{self.done:{self.digits}d}/{self.total}"
        shared = common_unit(self.done, self.total or 0)
        return (f"{self.amount(self.done, size_unit=shared)}"
                f"/{self.amount(self.total or 0, size_unit=shared)}")

    def parts(self) -> list[str | BarSlot]:
        fields: list[str | BarSlot] = [self.desc] if self.desc else []
        rate = self.rate
        if self.total:
            fields += [self.counter(),
                       BarSlot(self.ratio, intensity=rate),
                       f"{self.ratio:4.0%}"]
        else:
            fields.append(self.amount(self.done))
        if rate > 0:
            fields.append(f"{self.amount(rate, decimals=1)}/s")
            if self.total:
                fields.append(f"{self.eta_label} {clock((self.total - self.done) / rate)}")
        return fields
