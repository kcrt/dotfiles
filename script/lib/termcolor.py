# -*- coding: utf-8 -*-
"""Terminal coloring, in both 24-bit (truecolor) and 256-color forms.

Colors are emitted only when the destination is a terminal that may receive them,
so callers never have to branch: piping to a file drops the escapes on its own.

24-bit and 256-color are separate because the conditions differ. Almost every
terminal can do 256 colors, but 24-bit cannot be assumed without looking at
COLORTERM. A script with a `--color` flag can override the whole decision through
set_color_mode().

Use the standard library only (see termtext for why).
"""

from __future__ import annotations

import colorsys
import os
import sys
from typing import TextIO

from .termtext import SGR_RESET, pad_display

RGB = tuple[int, int, int]

# Default display width for the status marker at the start of a line (NG / skip / warning).
MARKER_WIDTH = 7

# Override from `--color always|never`. None means auto-detect.
_FORCED: bool | None = None


def set_color_mode(mode: str) -> None:
    """Interpret `--color auto|always|never` and pin every later decision to it.

    `always` colors even when the destination is not a terminal (for `less -R`, or
    for keeping the colors in a file).
    """
    global _FORCED
    try:
        _FORCED = {"always": True, "never": False, "auto": None}[mode]
    except KeyError:
        raise ValueError(f"色の指定が不正です: {mode!r}（auto/always/never）") from None


def color_enabled(stream: TextIO | None = None) -> bool:
    """Whether this destination may receive color (up to 256 colors).

    NO_COLOR (https://no-color.org/) and TERM=dumb are honored.
    Pipes and files drop the color so it does not end up mixed into the content.
    """
    if _FORCED is not None:
        return _FORCED
    stream = stream or sys.stdout
    if os.environ.get("NO_COLOR") or os.environ.get("TERM") == "dumb":
        return False
    return stream.isatty()


def use_color_for(stream: TextIO) -> bool:
    """Whether this destination may receive 24-bit color.

    Terminal.app does not understand the colon-separated subparameter form
    (38:2::r:g:b), so always spell these with semicolons. The check looks only at
    COLORTERM, which is conservative: when in doubt, fall back to plain output.

    stdout and stderr are decided separately. Error lines go to stderr, so judging
    by stdout alone would leak escapes into `cmd 2> err.log`.
    """
    if not color_enabled(stream):
        return False
    if _FORCED:
        return True        # `--color always` is taken as "24-bit too"
    return os.environ.get("COLORTERM", "").lower() in ("truecolor", "24bit")


def use_color() -> bool:
    """Whether stdout may receive 24-bit color."""
    return use_color_for(sys.stdout)


def sgr(rgb: RGB) -> str:
    """Escape sequence setting the foreground color (24-bit)."""
    return f"\033[38;2;{rgb[0]};{rgb[1]};{rgb[2]}m"


def sgr256(code: int) -> str:
    """Escape sequence setting the foreground color (256-color palette index)."""
    return f"\033[38;5;{code}m"


# The basic 16 foreground colors. Unlike the 256-color palette and 24-bit color,
# these follow the user's terminal theme, so a green tick looks native in both a
# light and a dark profile. The bright half is the same eight plus 60.
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(30, 38)
(BRIGHT_BLACK, BRIGHT_RED, BRIGHT_GREEN, BRIGHT_YELLOW,
 BRIGHT_BLUE, BRIGHT_MAGENTA, BRIGHT_CYAN, BRIGHT_WHITE) = range(90, 98)

# Bold (or bright, depending on the terminal). Not a color, so it composes with one.
SGR_BOLD = "\033[1m"


def sgr16(code: int) -> str:
    """Escape sequence setting the foreground color (one of the basic 16)."""
    return f"\033[{code}m"


def paint(text: str, rgb: RGB, stream: TextIO | None = None) -> str:
    """Color the text if the terminal takes 24-bit color, otherwise return it unchanged."""
    return (f"{sgr(rgb)}{text}{SGR_RESET}"
            if use_color_for(stream or sys.stdout) else text)


def paint256(text: str, code: int, stream: TextIO | None = None) -> str:
    """Color the text from the 256-color palette, or return it unchanged if color is off."""
    return (f"{sgr256(code)}{text}{SGR_RESET}"
            if color_enabled(stream) else text)


def paint16(text: str, code: int, stream: TextIO | None = None) -> str:
    """Color the text with one of the basic 16, or return it unchanged if color is off."""
    return (f"{sgr16(code)}{text}{SGR_RESET}"
            if color_enabled(stream) else text)


def bold(text: str, stream: TextIO | None = None) -> str:
    """Embolden the text, or return it unchanged if the destination takes no escapes."""
    return f"{SGR_BOLD}{text}{SGR_RESET}" if color_enabled(stream) else text


def hue_rgb(hue: float, saturation: float = 0.85, value: float = 1.0) -> RGB:
    """RGB from a position on the color wheel (0-1; values outside wrap around)."""
    r, g, b = colorsys.hsv_to_rgb(hue % 1.0, saturation, value)
    return (round(r * 255), round(g * 255), round(b * 255))


def scale_rgb(rgb: RGB, level: float) -> RGB:
    """Scale the brightness by `level` (1.0 keeps the original color). Clamped at 255."""
    return (min(255, round(rgb[0] * level)),
            min(255, round(rgb[1] * level)),
            min(255, round(rgb[2] * level)))


def status_line(marker: str, rgb: RGB | None, text: str,
                stream: TextIO | None = None, width: int = MARKER_WIDTH) -> str:
    """Build "  NG     name: reason", coloring the marker only.

    Alignment is left to display_width (which does not count color escapes), so the
    column never shifts depending on whether color is on.
    """
    painted = paint(marker, rgb, stream) if rgb else marker
    return f"  {pad_display(painted, width)}{text}"
