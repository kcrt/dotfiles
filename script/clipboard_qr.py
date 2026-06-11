#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "pillow",
#     "pyzbar",
# ]
# ///

"""
Clipboard QR Code Reader

Reads an image from the clipboard, recognizes QR codes, and outputs the results.
"""

import ctypes.util
import platform
import sys
from pathlib import Path


# macOS SIP strips DYLD_* env vars when the script is launched via /usr/bin/env,
# so pyzbar's ctypes.util.find_library('zbar') cannot locate the Homebrew-installed
# libzbar.dylib. Patch find_library to fall back to known Homebrew locations.
if platform.system() == "Darwin":
    _orig_find_library = ctypes.util.find_library

    def _find_library_with_brew_fallback(name: str) -> str | None:
        found = _orig_find_library(name)
        if found is not None or name != "zbar":
            return found
        for candidate in ("/opt/homebrew/lib/libzbar.dylib", "/usr/local/lib/libzbar.dylib"):
            if Path(candidate).exists():
                return candidate
        return None

    ctypes.util.find_library = _find_library_with_brew_fallback

from PIL import ImageGrab
from pyzbar import pyzbar


def read_qr_codes_from_clipboard() -> list[str]:
    """
    Read QR codes from the clipboard image.

    Returns:
        A list of decoded QR code data strings.

    Raises:
        RuntimeError: If no image is found on the clipboard.
    """
    # Grab image from clipboard
    img = ImageGrab.grabclipboard()

    if img is None:
        raise RuntimeError("No image found on clipboard. Please copy an image first.")

    # Handle case where clipboard contains a file path instead of image data
    if isinstance(img, list):
        raise RuntimeError(
            "Clipboard contains file paths, not image data. "
            "Please copy the actual image content."
        )

    # Convert to RGB if necessary (pyzbar requires RGB or grayscale)
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Decode QR codes
    decoded_objects = pyzbar.decode(img)

    if not decoded_objects:
        return []

    return [obj.data.decode("utf-8") for obj in decoded_objects]


def main() -> None:
    """Main entry point."""
    try:
        results = read_qr_codes_from_clipboard()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if not results:
        print("No QR codes found in the clipboard image.")
        sys.exit(0)

    # Output results
    for i, result in enumerate(results, 1):
        if len(results) > 1:
            print(f"[{i}] {result}")
        else:
            print(result)


if __name__ == "__main__":
    main()
