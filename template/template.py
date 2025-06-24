#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-

import argparse

def parsearg():
    parser = argparse.ArgumentParser(description="A template script.")
    parser.add_argument('--version', action='version', version='%(prog)s 0.1')
    return parser.parse_args()

def main():
    args = parsearg()
    print("Hello, world")

if __name__ == '__main__':
    main()
