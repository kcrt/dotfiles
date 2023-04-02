#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Convert text in various ways
#

import argparse
import base64
import urllib.parse
import sys
import codecs
import quopri
import html

MODES = ['all', 'upper', 'lower', 'title', 'reverse',
         'rot13', 'urldecode', 'urlencode', 'base64encode', 'base64decode', 'base64urlencode', 'base64urldecode', 'qpencode', 'qpdecode', 'hexencode', 'hexdecode', 'escapeunicode', 'unescapeunicode', 'topunycode', 'frompunycode', 'tobraille', 'frombraille', 'tohtmlentities', 'fromhtmlentities', 'tomorse', 'frommorse']

braille_map = {
    'a': '⠁', 'b': '⠃', 'c': '⠉', 'd': '⠙', 'e': '⠑', 'f': '⠋',
    'g': '⠛', 'h': '⠓', 'i': '⠊', 'j': '⠚', 'k': '⠅', 'l': '⠇',
    'm': '⠍', 'n': '⠝', 'o': '⠕', 'p': '⠏', 'q': '⠟', 'r': '⠗',
    's': '⠎', 't': '⠞', 'u': '⠥', 'v': '⠧', 'w': '⠺', 'x': '⠭',
    'y': '⠽', 'z': '⠵', ' ': '⠀', ',': '⠂', '.': '⠲', '?': '⠦',
    '!': '⠖', "'": '⠄', '"': '⠄', '(': '⠷', ')': '⠾', '-': '⠤',
    '/': '⠴', ':': '⠱', ';': '⠮', '=': '⠼', '+': '⠠', '*': '⠰',
    '&': '⠈', '%': '⠨', '$': '⠄', '#': '⠄', '@': '⠄', '0': '⠴',
    '1': '⠂', '2': '⠆', '3': '⠒', '4': '⠲', '5': '⠢', '6': '⠖',
    '7': '⠶', '8': '⠦', '9': '⠔'
}
morse_map = {
    'a': '.-', 'b': '-...', 'c': '-.-.', 'd': '-..', 'e': '.',
    'f': '..-.', 'g': '--.', 'h': '....', 'i': '..', 'j': '.---',
    'k': '-.-', 'l': '.-..', 'm': '--', 'n': '-.', 'o': '---',
    'p': '.--.', 'q': '--.-', 'r': '.-.', 's': '...', 't': '-',
    'u': '..-', 'v': '...-', 'w': '.--', 'x': '-..-', 'y': '-.--',
    'z': '--..', ' ': ' ', ',': '--..--', '.': '.-.-.-', '?': '..--..',
    '!': '-.-.--', "'": '.----.', '"': '.-..-.', '(': '-.--.-',
    ')': '-.--.-', '-': '-....-', '/': '-..-.', ':': '---...', ';': '-.-.-.',
    '=': '-...-', '+': '.-.-.', '*': '-..-', '&': '.-...', '%': '.-.-.',
    '$': '...-..-', '#': '-.-.-.', '@': '.--.-.', '0': '-----',
    '1': '.----', '2': '..---', '3': '...--', '4': '....-', '5': '.....',
    '6': '-....', '7': '--...', '8': '---..', '9': '----.'
}


def parse_args():
    parser = argparse.ArgumentParser(
        description='Convert text in various ways')
    parser.add_argument('mode', help='Conversion mode',
                        nargs='?', choices=MODES, default='all')
    return parser.parse_args()


def convert(text, mode):
    if mode == 'upper':
        return text.upper()
    elif mode == 'lower':
        return text.lower()
    elif mode == 'title':
        return text.title()
    elif mode == 'reverse':
        return text[::-1]
    elif mode == 'rot13':
        return codecs.encode(text, 'rot13')
    elif mode == 'urldecode':
        return urllib.parse.unquote(text)
    elif mode == 'urlencode':
        return urllib.parse.quote(text)
    elif mode == 'base64encode':
        return base64.b64encode(text.encode('utf-8')).decode('utf-8')
    elif mode == 'base64decode':
        try:
            return base64.b64decode(text.encode('utf-8')).decode('utf-8')
        except Exception:
            return "(invalid)"
    elif mode == 'base64urlencode':
        return base64.urlsafe_b64encode(text.encode('utf-8')).decode('utf-8')
    elif mode == 'base64urldecode':
        try:
            return base64.urlsafe_b64decode(text.encode('utf-8')).decode('utf-8')
        except Exception:
            return "(invalid)"
    elif mode == 'qpencode':
        return quopri.encodestring(text.encode('utf-8')).decode('utf-8')
    elif mode == 'qpdecode':
        try:
            return quopri.decodestring(text.encode('utf-8')).decode('utf-8')
        except Exception:
            return "(invalid)"
    elif mode == 'hexencode':
        return text.encode('utf-8').hex()
    elif mode == 'hexdecode':
        try:
            return bytes.fromhex(text).decode('utf-8')
        except Exception:
            return "(invalid)"
    elif mode == 'uuencode':
        return codecs.encode(text.encode('utf-8'), 'uu').decode('utf-8')
    elif mode == 'uudecode':
        try:
            return codecs.decode(text.encode('utf-8'), 'uu').decode('utf-8')
        except Exception:
            return "(invalid)"
    elif mode == 'escapeunicode':
        return text.encode('unicode_escape').decode('utf-8')
    elif mode == 'unescapeunicode':
        try:
            return text.encode('utf-8').decode('unicode_escape')
        except Exception:
            return "(invalid)"
    elif mode == 'topunycode':
        return text.encode('punycode').decode('utf-8')
    elif mode == 'frompunycode':
        try:
            return text.encode('utf-8').decode('punycode')
        except Exception:
            return "(invalid)"
    elif mode == 'tobraille':
        return "".join([braille_map.get(c, c) for c in text.lower()])
    elif mode == 'frombraille':
        braille_map_rev = {v: k for k, v in braille_map.items()}
        return "".join([braille_map_rev.get(c, c) for c in text.lower()])
    elif mode == 'tohtmlentities':
        return html.escape(text)
    elif mode == 'fromhtmlentities':
        try:
            return html.unescape(text)
        except Exception:
            return "(invalid)"
    elif mode == 'tomorse':
        return " ".join([morse_map.get(c, c) for c in text.lower()])
    elif mode == 'frommorse':
        morse_map_rev = {v: k for k, v in morse_map.items()}
        text = text.replace("  ", " <space> ")
        return "".join([morse_map_rev.get(c, c) for c in text.lower().split(" ")]).replace("<space>", " ")
    else:
        raise ValueError('Invalid mode: {}'.format(mode))


def main():
    args = parse_args()
    text = input()

    if args.mode == "all":
        # print to stderr
        for mode in MODES[1:]:
            print(f"{mode:>15s}: {convert(text, mode)}", file=sys.stderr)
    else:
        print(convert(text, args.mode))


if __name__ == '__main__':
    main()
