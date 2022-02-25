#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from collections import defaultdict

parser = argparse.ArgumentParser(description="Omit rare case")
parser.add_argument("n", help="Threshold.")
args = parser.parse_args()

def main():
    d = defaultdict(int)
    while True:
        try:
            l = input()
        except EOFError:
            break
        d[l] += 1
    for l in d:
        if d[l] >= int(args.n):
            print(l)

if __name__ == '__main__':
    main()

