# -*- coding: utf-8 -*-
"""Display-width arithmetic for text laid out in a terminal.

len() does not line up columns once a line contains Japanese: full-width
characters take two cells, and color escapes (SGR) take none. This module
counts, pads and cuts with both of those in mind.

Use the standard library only. PEP 723 `dependencies` can only be declared by
the script being run, so a third-party import here would force every script
that imports lib.* to repeat the same dependency list.
"""

from __future__ import annotations

import re
import unicodedata

# SGR (color) sequences. They occupy no display cells, so strip them before counting.
SGR_PATTERN = re.compile(r"\x1b\[[0-9;]*m")

# Reset to the default color. Appended when a cut lands inside a colored run.
# termcolor spells its escapes through this constant too: keeping it here holds the
# dependency to termcolor -> termtext only, with no import going back the other way.
SGR_RESET = "\033[0m"

# Marker for "there was more text". Takes one cell.
ELLIPSIS = "…"


def char_width(ch: str) -> int:
    """Display width of a single character in the terminal.

    Combining marks (dakuten and friends) sit on top of the previous character, so
    they are 0 cells. macOS filenames arrive in NFD, where "が" is "か" plus a
    combining dakuten: counting that as one 2-cell character would over-estimate
    Japanese filenames and break the column alignment.

    Full-width (W/F) is 2 cells. Ambiguous width (A: box drawing, ★, block
    characters) is treated as 1 cell, matching the default terminal setting.
    """
    if unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in "WF" else 1


def display_width(text: str) -> int:
    """Display width in the terminal, counting full-width characters as 2 cells.

    Color escapes (SGR) take no cells, so they are stripped before counting.
    """
    return sum(char_width(ch) for ch in SGR_PATTERN.sub("", text))


def strip_sgr(text: str) -> str:
    """The plain text with color escapes removed. For logs and files."""
    return SGR_PATTERN.sub("", text)


def pad_display(text: str, width: int) -> str:
    """Pad on the right with spaces up to `width`. Unchanged if already wider."""
    return text + " " * max(width - display_width(text), 0)


def truncate_display(text: str, limit: int) -> str:
    """Drop the tail so the display width stays within `limit`.

    Keeps a progress line from wrapping onto a second row.

    Color escapes (SGR) take no cells and are passed through. If the cut lands
    inside a colored run, a reset is appended so no color leaks into the terminal.
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
    """Cut to fit `width` without splitting a full-width character in half.

    Returns the cut text and its actual display width (the caller uses the width to
    pad: cutting before a full-width character can land one cell short of `width`,
    and this saves counting it again).
    Unlike truncate_display, no "…" is added. For fixed columns in a TUI, where
    keeping the grid aligned matters more than showing that text was cut.
    """
    used = 0
    for index, ch in enumerate(text):
        w = char_width(ch)
        if used + w > width:
            return text[:index], used
        used += w
    return text, used


def fit_display(text: str, width: int, align: str = "<") -> str:
    """Make the display width exactly `width`: cut if longer, pad if shorter.

    For tables with fixed column widths, so the caller need not branch between
    cutting and padding. align=">" right-aligns.
    """
    width = max(0, width)
    body, used = clip_display(text, width)
    padding = " " * (width - used)
    return padding + body if align == ">" else body + padding
