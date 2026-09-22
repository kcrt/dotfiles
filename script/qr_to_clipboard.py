#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "qrcode",
#     "pillow",
# ]
# ///
"""Turn stdin into a QR code image and put it on the clipboard.

The counterpart of clipboard_qr.py, which reads a QR code out of the clipboard.
Together they move a URL, a Wi-Fi password or a one-time code between this
machine and a phone without either of them leaving the desk.

    pbpaste | ./qr_to_clipboard.py              # whatever is on the clipboard
    ./qr_to_clipboard.py 'https://example.com'  # or straight from the argument
    ip a | ./qr_to_clipboard.py -p              # -p also draws it in the terminal
    ./qr_to_clipboard.py -o qr.png 'hello'      # keep the PNG as well

One trailing newline is dropped so a piped `echo` does not encode an invisible
extra byte; --raw keeps stdin exactly as it arrived. Data that is not UTF-8 is
encoded in the QR code's byte mode.
"""

from __future__ import annotations

import argparse
import io
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import qrcode
from qrcode.exceptions import DataOverflowError
from qrcode.constants import (ERROR_CORRECT_H, ERROR_CORRECT_L, ERROR_CORRECT_M,
                              ERROR_CORRECT_Q)

# How much of the code can be lost and still read: L 7%, M 15%, Q 25%, H 30%.
# More correction means a denser code for the same data.
ERROR_CORRECTION = {"L": ERROR_CORRECT_L, "M": ERROR_CORRECT_M,
                    "Q": ERROR_CORRECT_Q, "H": ERROR_CORRECT_H}

# Four modules of quiet zone, the minimum the QR standard asks for. Without it
# scanners fail on a code sitting against other content.
DEFAULT_BORDER = 4


class ClipboardError(RuntimeError):
    """The image could not be handed to the clipboard."""


def build_qr(data: bytes, error_correction: str, box_size: int, border: int) -> qrcode.QRCode:
    """Make the QR code, letting the library pick the smallest version that fits.

    Text is passed as str so the library can use the compact numeric and
    alphanumeric modes where the content allows; anything else goes as bytes.
    """
    try:
        payload: str | bytes = data.decode("utf-8")
    except UnicodeDecodeError:
        payload = data

    code = qrcode.QRCode(error_correction=ERROR_CORRECTION[error_correction],
                         box_size=box_size, border=border)
    code.add_data(payload)
    code.make(fit=True)
    return code


def png_bytes(code: qrcode.QRCode) -> bytes:
    """Render the code as a PNG in memory."""
    buffer = io.BytesIO()
    code.make_image(fill_color="black", back_color="white").save(buffer, format="PNG")
    return buffer.getvalue()


def copy_png_to_clipboard(png: bytes) -> None:
    """Put a PNG image (not a file path) on the clipboard.

    macOS has no pbcopy equivalent for images, so this goes through AppleScript,
    which needs the bytes in a file. Wayland and X11 take the PNG on stdin.
    """
    system = platform.system()
    if system == "Darwin":
        _copy_png_macos(png)
        return
    for command in (["wl-copy", "--type", "image/png"],
                    ["xclip", "-selection", "clipboard", "-t", "image/png"]):
        if shutil.which(command[0]):
            subprocess.run(command, input=png, check=True)
            return
    raise ClipboardError(
        f"no way to reach the clipboard on {system}: install wl-clipboard or xclip")


def _copy_png_macos(png: bytes) -> None:
    with tempfile.TemporaryDirectory() as workdir:
        path = Path(workdir) / "qr.png"
        path.write_bytes(png)
        # The path goes inside an AppleScript string literal. mkdtemp() never
        # puts a quote or a backslash in it, but a changed TMPDIR could, and
        # that would end the literal early.
        if '"' in str(path) or "\\" in str(path):
            raise ClipboardError(f"temporary path is not safe for AppleScript: {path}")
        script = f'set the clipboard to (read (POSIX file "{path}") as «class PNGf»)'
        result = subprocess.run(["osascript", "-e", script],
                                capture_output=True, text=True)
        if result.returncode != 0:
            raise ClipboardError(result.stderr.strip() or "osascript failed")


def read_input(arguments: list[str], raw: bool) -> bytes:
    """The data to encode: the arguments joined by spaces, or all of stdin."""
    if arguments:
        return " ".join(arguments).encode("utf-8")
    data = sys.stdin.buffer.read()
    if not raw and data.endswith(b"\n"):
        data = data[:-1]
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="QR-encode stdin and copy the image to the clipboard.",
        epilog="Input comes from stdin when no text is given.")
    parser.add_argument("text", nargs="*",
                        help="text to encode (default: read stdin)")
    parser.add_argument("-e", "--error-correction", choices=tuple(ERROR_CORRECTION),
                        default="M", help="recovery level, L/M/Q/H (default: M)")
    parser.add_argument("-s", "--size", type=int, default=8, metavar="PIXELS",
                        help="pixels per module (default: 8)")
    parser.add_argument("-b", "--border", type=int, default=DEFAULT_BORDER,
                        metavar="MODULES",
                        help=f"quiet zone in modules (default: {DEFAULT_BORDER})")
    parser.add_argument("-o", "--output", type=Path, metavar="PATH",
                        help="also write the PNG here")
    parser.add_argument("-p", "--print", action="store_true", dest="draw",
                        help="also draw the code in the terminal")
    parser.add_argument("--no-copy", action="store_true",
                        help="skip the clipboard (useful with -o or -p)")
    parser.add_argument("--raw", action="store_true",
                        help="keep the trailing newline of stdin instead of dropping it")
    return parser.parse_args()


def main() -> int:
    options = parse_args()
    data = read_input(options.text, options.raw)
    if not data:
        print("Error: nothing to encode.", file=sys.stderr)
        return 1
    if options.border < DEFAULT_BORDER:
        print(f"Warning: a border under {DEFAULT_BORDER} modules may not scan.",
              file=sys.stderr)

    try:
        code = build_qr(data, options.error_correction, options.size, options.border)
    except (DataOverflowError, ValueError):
        # Too much data shows up two ways: DataOverflowError when the version is
        # pinned, and a plain ValueError("Invalid version") from the search for a
        # fitting version, which is the path taken here.
        print(f"Error: {len(data)} bytes do not fit in a QR code at level "
              f"{options.error_correction} (the largest holds 2953 bytes at level L, "
              f"1273 at H). Try -e L, or encode less.", file=sys.stderr)
        return 1

    if options.draw:
        code.print_ascii(out=sys.stdout)
    if options.output:
        options.output.write_bytes(png_bytes(code))
        print(f"Wrote {options.output}", file=sys.stderr)
    if not options.no_copy:
        try:
            copy_png_to_clipboard(png_bytes(code))
        except (ClipboardError, subprocess.CalledProcessError) as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1
        # On stderr so the script stays usable in a pipeline.
        modules = code.modules_count
        print(f"Copied a {modules}x{modules} QR code ({len(data)} bytes, "
              f"level {options.error_correction}) to the clipboard.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
