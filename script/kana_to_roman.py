#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# dependencies = [
#   "jaconv",
#   "pykakasi",
# ]
# ///

import sys
import argparse
from typing import TextIO
import pykakasi


def kana_to_roman(text: str, use_hepburn: bool = True) -> str:
    """Convert kana (hiragana or katakana) to romanized string.

    Args:
        text: Input text containing kana characters
        use_hepburn: If True, use Hepburn romanization; otherwise use Kunrei-shiki

    Returns:
        Romanized string
    """
    kks = pykakasi.kakasi()
    result = kks.convert(text)
    key = 'hepburn' if use_hepburn else 'kunrei'
    return ''.join([item[key] for item in result])


def main() -> None:
    """Read kana from stdin and output romanized text to stdout."""
    parser = argparse.ArgumentParser(description="Convert kana to romanized text.")
    parser.add_argument('--non-hepburn', action='store_true',
                        help='Use Kunrei-shiki romanization instead of Hepburn')
    args = parser.parse_args()

    input_stream: TextIO = sys.stdin

    for line in input_stream:
        romanized = kana_to_roman(line.rstrip('\n'), use_hepburn=not args.non_hepburn)
        print(romanized)


if __name__ == '__main__':
    main()
