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
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Print caesar cipher with key of 1 to 25')
    parser.add_argument('--mode', choices=['all', 'key'])
    parser.add_argument('--keys', nargs='?', type=str,
                        help='keys: e.g. "12 2 0 4"')
    parser.add_argument('--rotate', nargs='?', type=int, help="shift key")
    return parser.parse_args()


def caesar(s, keys):
    """
    Perform Caesar cipher encryption/decryption
    
    Args:
        s (str): Input string to process
        keys (int or list): Shift value(s) to apply
    
    Returns:
        str: Processed string with Caesar cipher applied
    """
    result = ''
    i = 0
    # Convert single key to list for consistent processing
    if not isinstance(keys, list):
        keys = [keys]

    for c in s:
        if c.isalpha():
            # Get current key based on position in the text
            current_key = keys[i % len(keys)]
            if c.isupper():
                # Process uppercase letters (A-Z)
                result += chr((ord(c) - ord('A') + current_key) % 26 + ord('A'))
            else:
                # Process lowercase letters (a-z)
                result += chr((ord(c) - ord('a') + current_key) % 26 + ord('a'))
            i += 1  # Only increment for alphabetic characters
        else:
            # Non-alphabetic characters remain unchanged
            result += c
    return result


def main():
    """Main function to process input text with Caesar cipher"""
    args = parse_args()
    s = input()  # Read input text from stdin
    
    # Default mode (ROT13)
    if args.mode is None:
        print(caesar(s, 13))
    # All possible shifts (1-25)
    elif args.mode == 'all':
        for i in range(1, 26):
            print(str(i) + ": " + caesar(s, i))
    # Custom key mode
    elif args.mode == 'key':
        # Parse space-separated key values
        keys = list(map(int, args.keys.split(' ')))
        if args.rotate:
            # Rotate key sequence if specified
            # e.g. [1 2 3] with rotate=1 becomes [2 3 1]
            keys = keys[args.rotate:] + keys[:args.rotate]
        print(caesar(s, keys))


if __name__ == '__main__':
    main()