#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
"""Convert to and from Crockford's Base32.

Crockford's Base32 (https://www.crockford.com/base32.html) drops I, L, O and U
from the alphabet, so a human reading a code aloud or typing it back cannot
confuse 1/I/l or 0/O, and cannot spell an accidental obscenity. Decoding is
therefore forgiving: the case does not matter, I and L read as 1, O reads as 0,
and hyphens put in for readability are ignored.

Two things can be encoded, and they give different strings for the same input:

    bytes     (the default) arbitrary data, 5 bits per symbol, as base32
              usually means. No "=" padding: Crockford has none.
    --number  a single non-negative integer, which is what the spec itself
              describes. The check symbol (-c) only exists in this mode.

    echo -n hello | ./crockford_base32.py           # D1JPRV3F
    ./crockford_base32.py -d D1JPRV3F               # hello
    ./crockford_base32.py -n 1234567890             # 14SC0PJ
    ./crockford_base32.py -n -c 1234567890          # 14SC0PJV  (trailing check)
    ./crockford_base32.py -n -d -c 14sc0pjv         # 1234567890
    ./crockford_base32.py -g 4 -n 1234567890        # 14SC-0PJ
    ./crockford_base32.py -d 'd1jp-rv3f'            # hello  (hyphens, lowercase)

Input comes from the arguments, or from stdin when there are none. One trailing
newline is dropped so `echo` behaves as expected; pass --raw to encode stdin
byte for byte.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import sys

# The 32 symbols, in value order. I, L, O and U are absent on purpose.
ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

# Five more symbols extend the alphabet to a prime 37 for the check symbol.
# U is safe here because a check symbol never appears inside the payload.
CHECK_ALPHABET = ALPHABET + "*~$=U"

# base64.b32encode speaks RFC 4648; the two alphabets differ only in spelling,
# so translating the symbols is enough to reuse its bit packing.
RFC4648_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
_TO_CROCKFORD = str.maketrans(RFC4648_ALPHABET, ALPHABET)
_FROM_CROCKFORD = str.maketrans(ALPHABET, RFC4648_ALPHABET)

# Applied after upper(): the confusable letters fold onto digits, and hyphens
# and spaces inserted for readability disappear.
_NORMALIZE = str.maketrans({"I": "1", "L": "1", "O": "0", "-": "", " ": ""})


class Base32Error(ValueError):
    """The text is not valid Crockford Base32."""


def normalize(text: str) -> str:
    """Fold a human-written code into bare alphabet symbols.

    Nothing is validated here beyond the symbols themselves being known, so a
    check symbol has to be taken off before calling this.
    """
    symbols = "".join(text.split()).upper().translate(_NORMALIZE)
    unknown = sorted(set(symbols) - set(ALPHABET))
    if unknown:
        raise Base32Error(f"not Base32 symbols: {' '.join(unknown)}")
    return symbols


def encode_bytes(data: bytes) -> str:
    """Encode arbitrary data, 5 bits per symbol, without padding."""
    return base64.b32encode(data).decode("ascii").rstrip("=").translate(_TO_CROCKFORD)


def decode_bytes(text: str) -> bytes:
    """Decode what encode_bytes() produced, hyphens and case notwithstanding."""
    symbols = normalize(text).translate(_FROM_CROCKFORD)
    padded = symbols + "=" * (-len(symbols) % 8)
    try:
        return base64.b32decode(padded)
    except binascii.Error as error:
        # The only way to get here is a symbol count that no byte string
        # produces (1, 3 or 6 more than a multiple of 8).
        raise Base32Error(f"truncated Base32: {error}") from error


def encode_number(value: int) -> str:
    """Encode a non-negative integer, most significant symbol first."""
    if value < 0:
        raise Base32Error("only a non-negative integer can be encoded")
    symbols = []
    while True:
        value, remainder = divmod(value, 32)
        symbols.append(ALPHABET[remainder])
        if value == 0:
            return "".join(reversed(symbols))


def decode_number(text: str) -> int:
    """Decode an integer; leading zeros are accepted and lost, as they carry nothing."""
    symbols = normalize(text)
    if not symbols:
        raise Base32Error("no symbols to decode")
    value = 0
    for symbol in symbols:
        value = value * 32 + ALPHABET.index(symbol)
    return value


def check_symbol(value: int) -> str:
    """The check symbol for an integer: its remainder modulo 37."""
    return CHECK_ALPHABET[value % 37]


def split_check_symbol(text: str) -> tuple[str, str]:
    """Separate a trailing check symbol from the payload it protects.

    It is taken off before normalize() because the five extra symbols are not
    in the payload alphabet, and because a trailing U must stay a U rather than
    be rejected as a letter the alphabet dropped.
    """
    stripped = "".join(text.split()).upper().rstrip("-")
    if not stripped:
        raise Base32Error("no check symbol present")
    symbol = stripped[-1]
    if symbol not in CHECK_ALPHABET:
        raise Base32Error(f"not a check symbol: {symbol}")
    return stripped[:-1], symbol


def group(text: str, size: int) -> str:
    """Hyphenate every `size` symbols, for a code meant to be read out or typed."""
    if size <= 0:
        return text
    return "-".join(text[at:at + size] for at in range(0, len(text), size))


def read_input(arguments: list[str], raw: bool) -> bytes:
    """The data to work on: the arguments joined by spaces, or all of stdin.

    Without --raw one trailing newline goes away, so a piped `echo` encodes what
    it looks like it encodes rather than an invisible extra byte.
    """
    if arguments:
        return " ".join(arguments).encode("utf-8")
    data = sys.stdin.buffer.read()
    if not raw and data.endswith(b"\n"):
        data = data[:-1]
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert to and from Crockford's Base32.",
        epilog="Input comes from stdin when no text is given.")
    parser.add_argument("text", nargs="*",
                        help="text to convert (default: read stdin)")
    parser.add_argument("-d", "--decode", action="store_true",
                        help="decode instead of encode")
    parser.add_argument("-n", "--number", action="store_true",
                        help="treat the value as a single non-negative integer")
    parser.add_argument("-c", "--check", action="store_true",
                        help="append (or verify and strip) the check symbol; needs --number")
    parser.add_argument("-g", "--group", type=int, default=0, metavar="N",
                        help="hyphenate the encoded output every N symbols")
    parser.add_argument("--raw", action="store_true",
                        help="keep the trailing newline of stdin instead of dropping it")
    options = parser.parse_args()
    if options.check and not options.number:
        parser.error("--check is defined for --number only")
    return options


def encode(options: argparse.Namespace) -> str:
    data = read_input(options.text, options.raw)
    if not options.number:
        return group(encode_bytes(data), options.group)

    text = data.decode("utf-8", errors="replace").strip()
    try:
        value = int(text, 0)   # 0 so that 0x2a and 0b1010 are accepted too
    except ValueError as error:
        raise Base32Error(f"not an integer: {text!r}") from error
    encoded = encode_number(value)
    if options.check:
        encoded += check_symbol(value)
    return group(encoded, options.group)


def decode(options: argparse.Namespace) -> bytes:
    text = read_input(options.text, raw=False).decode("utf-8", errors="replace")
    if not options.number:
        return decode_bytes(text)

    if options.check:
        text, given = split_check_symbol(text)
        value = decode_number(text)
        expected = check_symbol(value)
        if given != expected:
            raise Base32Error(f"check symbol is {given}, expected {expected}")
    else:
        value = decode_number(text)
    return str(value).encode("ascii")


def main() -> int:
    options = parse_args()
    try:
        if options.decode:
            output = decode(options)
            # Decoded data is whatever was encoded, so a newline of ours would
            # be a byte the original did not have. Text output can have one.
            terminate = options.number or sys.stdout.isatty()
        else:
            output = encode(options).encode("utf-8")
            terminate = True
    except Base32Error as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    # Written as bytes: decoding arbitrary data can yield anything, including
    # bytes that are not text at all.
    sys.stdout.buffer.write(output)
    if terminate and not output.endswith(b"\n"):
        sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
