# -*- coding: utf-8 -*-
"""Render byte counts and durations in a form people can read.

It also covers showing a before/after pair (source -> destination plus the
reduction). The align variants fix the field width so digits line up vertically.

Use the standard library only (see termtext for why).
"""

from __future__ import annotations

from typing import TextIO

from .termcolor import RGB, paint

SIZE_UNITS = ("B", "KB", "MB", "GB", "TB", "PB")

# Cells reserved for the number part of a size. The unit is chosen from the larger
# value, so every value stays below 1024 and "1023.9" - six cells - is the widest.
SIZE_NUMBER_WIDTH = 6

# Color marking that the conversion grew the file. Orange.
GREW_RGB = (220, 130, 30)


def size_unit(n: float) -> str:
    """The unit that renders this byte count most readably."""
    for unit in SIZE_UNITS[:-1]:
        if abs(n) < 1024:
            return unit
        n /= 1024
    return SIZE_UNITS[-1]


def common_unit(*sizes: float) -> str:
    """The shared unit to use when several sizes are shown side by side.

    Chosen from the largest. Choosing from the smallest makes the larger side
    overflow its field once the ratio widens ("26774.3 KB") and breaks the column.
    Digits on the smaller side are preserved by human(), which adds a decimal place.
    """
    return size_unit(max(sizes))


def human(n: float, unit: str | None = None, align: bool = False,
          sep: str = " ") -> str:
    """Render a byte count in a readable unit.

    Passing `unit` forces that unit. When a before/after pair uses mismatched
    units, "1.0 MB → 194.0 KB" reads as if the file grew, so the two sides are
    aligned to one unit (picked with common_unit).
    align=True right-aligns the number and left-aligns the unit at a fixed width,
    so stacked result lines line up (`sep` is unused in this mode).
    sep="" gives the "1.5MB" form, for dropping into a right-aligned field outside.
    """
    unit = unit or size_unit(n)
    value = n / 1024 ** SIZE_UNITS.index(unit)
    # Below 1, add a decimal place. Aligning to the larger side's unit would squash
    # the smaller one into "0.9 MB", so keep two significant digits. The width is
    # the same either way, so the column stays aligned.
    decimals = 2 if 0 < abs(value) < 1 else 1
    return (f"{value:{SIZE_NUMBER_WIDTH}.{decimals}f} {unit:<2}" if align
            else f"{value:.{decimals}f}{sep}{unit}")


def size_change(src_size: int, dst_size: int, show_saved: bool = False,
                grew_rgb: RGB = GREW_RGB, stream: TextIO | None = None) -> str:
    """Build "  1.3 MB →  800.0 KB ( 60%)", with one unit shared by both sides.

    Result lines and the total line use the same fields at the same widths, so the
    formatting lives in this one place.
    show_saved=True also puts the absolute change inside the parentheses (for the
    total line).
    `stream` is where the line is headed, since that is what decides whether the
    color may be spelled at all - pass it whenever the line is not going to stdout.

    When the conversion grew the file, the text says 増加 and the whole parenthesis
    is colored: a negative reduction ("-113.3 MB 削減") takes a beat to read and is
    easy to miss.
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
        change = paint(change, grew_rgb, stream)
    return (f"{human(src_size, unit, align=True)} → {human(dst_size, unit, align=True)} "
            f"{change}")


def clock(seconds: float, always_hours: bool = False) -> str:
    """Render seconds as 1:02:03 / 2:03.

    always_hours=True keeps a zero-padded hour field (00:02:03). Use it for a
    column of values, where dropping the hours on the short ones would leave the
    colons unaligned once a later one crosses an hour.
    """
    total = int(max(seconds, 0))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if always_hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"
