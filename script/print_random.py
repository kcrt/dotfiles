#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random


def main():

    while True:
        hash = random.getrandbits(128)
        print("%032x" % hash)


if __name__ == '__main__':
    main()
