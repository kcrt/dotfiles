#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse

def main():
    parser = argparse.ArgumentParser(description="Process text automatically")
    parser.add_argument('integers', metavar='N', type=int, nargs='+',
                                help='an integer for the accumulator')
    parser.add_argument('--sum', dest='accumulate', action='store_const',
                                const=sum, default=max,
                                                    help='sum the integers (default: find the max)')

    args = parser.parse_args()
    print(args.accumulate(args.integers))
    print("Hello, world")

if __name__ == '__main__':
    main()

