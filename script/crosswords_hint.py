#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-

import argparse
import os
import re

WORDS_LIST = {
    "en": "~/data/english_words.txt",
    "ja": "~/data/mecab-japanesewords.tsv"
}

# English list:
# ```
# aglaia
# aglauros
# aglaus
# agle
# agleaf
#  ...
# ```

# Japanese list:
# ```
# カセイソーダ	苛性ソーダ
# カセガワ	加勢川
# カセキ	化石
# カセキサイ	過積載
# カセギ	稼ぎ
# カセダ	加世田
# カセダヒガシ	笠田東
# カセット	カセット
# カセットテープ	カセットテープ
# ```

def parsearg():
    parser = argparse.ArgumentParser(description="Crosswords hint matcher with wildcard support.")
    parser.add_argument('--version', action='version', version='%(prog)s 0.1')
    
    # Language selection
    lang_group = parser.add_mutually_exclusive_group(required=True)
    lang_group.add_argument('--ja', action='store_true', help='Use Japanese word list')
    lang_group.add_argument('--en', action='store_true', help='Use English word list')
    
    # Ruby-only option for Japanese
    parser.add_argument('--ruby-only', action='store_true', help='Output only ruby for Japanese words (ignored for English)')
    
    # Hint pattern
    parser.add_argument('hint', help='Pattern to match (? = any character, * = any string)')
    
    return parser.parse_args()

def pattern_to_regex(pattern):
    """Convert crossword pattern to regex pattern.
    ? matches any single character
    * matches any string (including empty)
    """
    # Escape special regex characters except ? and *
    escaped = re.escape(pattern)
    # Replace escaped ? and * with their regex equivalents
    regex_pattern = escaped.replace(r'\?', '.').replace(r'\*', '.*')
    return f'^{regex_pattern}$'

def match_english_words(pattern, words_file):
    """Match English words against pattern."""
    regex = re.compile(pattern_to_regex(pattern), re.IGNORECASE)
    matches = []
    
    try:
        with open(os.path.expanduser(words_file), 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip()
                if word and regex.match(word):
                    matches.append(word)
    except FileNotFoundError:
        print(f"Error: Word list file not found: {words_file}")
        return []
    
    return matches

def match_japanese_words(pattern, words_file):
    """Match Japanese words against pattern, return both ruby and kanji."""
    regex = re.compile(pattern_to_regex(pattern), re.IGNORECASE)
    matches = []
    
    try:
        with open(os.path.expanduser(words_file), 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    ruby = parts[0]
                    kanji = parts[1]
                    if regex.match(ruby):
                        matches.append((ruby, kanji))
    except FileNotFoundError:
        print(f"Error: Word list file not found: {words_file}")
        return []
    
    return matches

def main():
    args = parsearg()
    
    language = "ja" if args.ja else "en"
    words_file = WORDS_LIST[language]
    pattern = args.hint
    
    if language == "en":
        matches = match_english_words(pattern, words_file)
        for word in matches:
            print(word)
    else:  # Japanese
        matches = match_japanese_words(pattern, words_file)
        if args.ruby_only:
            seen_ruby = set()
            for ruby, kanji in matches:
                if ruby not in seen_ruby:
                    print(ruby)
                    seen_ruby.add(ruby)
        else:
            for ruby, kanji in matches:
                print(f"{ruby}\t{kanji}")

if __name__ == '__main__':
    main()

