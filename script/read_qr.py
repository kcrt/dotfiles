#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Read and decode QR code from image file

from PIL import Image
import argparse
import pyzbar.pyzbar as pyzbar


def parse_args():
    parser = argparse.ArgumentParser(
        description='Read and decode QR code from image file')
    parser.add_argument('image', help='image file')
    return parser.parse_args()


def main():
    args = parse_args()
    image = Image.open(args.image)

    decoded_objects = pyzbar.decode(image)
    for obj in decoded_objects:
        print('Type:', obj.type)
        print('Data:', obj.data.decode('utf-8'))
        print("----")


if __name__ == '__main__':
    main()
