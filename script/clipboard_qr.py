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

import sys
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
