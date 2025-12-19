#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pillow",
#     "tqdm",
# ]
# ///

import glob
from statistics import median
from tqdm import tqdm
from PIL import Image

(width, height) = (-1, -1)
pixlist = []

for filename in tqdm(glob.glob("*.png"), ascii=True):
    print("loading " + filename)
    im = Image.open(filename)
    if(width == -1 or height == -1):
        (width, height) = im.size
        pixlist = [[[] for y in range(height)] for x in range(width)]
    elif(width != im.width or height != im.height):
        print("ERROR different image size: " + filename)
        exit()
    for x in range(width):
        for y in range(height):
            pixlist[x][y].append(im.getpixel((x, y)))
    im.close()


def xmedian(ts):
    n_items = len(ts[0])
    ret = []
    for i in range(n_items):
        a = []
        for j in range(len(ts)):
            a.append(ts[j][i])
        ret.append(int(median(a)))
    return tuple(ret)


newim = Image.new("RGB", (width, height))
for x in tqdm(range(width), ascii=True):
    for y in range(height):
        newim.putpixel((x, y), xmedian(pixlist[x][y]))

newim.save("median.png", "PNG")
