#!/usr/bin/env python3

import unicodedata
from getch import getch

while(True):
    c = getch()
    if c == "":
        break
    elif c == "\n" or c == "\r":
        print("----\t----\t----")
    elif c == "\ufe0e":
        pass
    else:
        code = hex(ord(c))
        info = unicodedata.name(c)
        print("{0}\ufe0e\t{0}\ufe0f\t{1}\t{2}".format(c, code, info))



