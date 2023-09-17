#!/usr/bin/env python3

# Print decrypted caesar cipher
# Characters other than alphabets are not converted
#
# Mode:
#   all: print all possible results (key: 1 to 25)
#   key: print result with given key (e.g. 12, 2, 0, 4)
#


import argparse


def parse_args():
    parser = argparse.ArgumentParser(
        description='Print caesar cipher with key of 1 to 25')
    parser.add_argument('--mode', choices=['all', 'key'])
    parser.add_argument('--keys', nargs='?', type=str,
                        help='keys: e.g. "12 2 0 4"')
    parser.add_argument('--rotate', nargs='?', type=int, help="shift key")
    return parser.parse_args()


def caesar(s, k):
    result = ''
    i = 0
    print(k)
    if not isinstance(k, list):
        keys = [k]
    else:
        keys = k

    for c in s:
        if c.isalpha():
            k = keys[i % len(keys)]
            if c.isupper():
                result += chr((ord(c) - ord('A') + k) % 26 + ord('A'))
            else:
                result += chr((ord(c) - ord('a') + k) % 26 + ord('a'))
            i += 1
        else:
            result += c
    return result


def main():
    args = parse_args()
    s = input()
    if args.mode == 'all':
        for i in range(1, 26):
            print(str(i) + ": " + caesar(s, i))
    elif args.mode == 'key':
        keys = list(map(int, args.keys.split(' ')))
        if args.rotate:
            # shift key, e.g. [1 2 3] -> [2 3 1]
            keys = keys[args.rotate:] + keys[:args.rotate]

        print(caesar(s, keys))

    pass


if __name__ == '__main__':
    main()
