#!/usr/bin/env python3

import argparse
import json
import subprocess

def br2mbs(bitrate):
    mbs = round(int(bitrate) / 8 / 1000 / 1000 * 60, 1)
    return f"{mbs} MiB/s"

def duration2hm(duration):
    duration = int(duration)
    minutes = (duration // 60) % 60
    hour = duration // 60 // 60
    return f"{hour:00}:{minutes:00}"

parser = argparse.ArgumentParser(description="Show size/minutes of movie.")
parser.add_argument("moviefile", help="Movie file to analyze")
args = parser.parse_args()

try:
    ret = subprocess.run(f'/usr/bin/env ffprobe -hide_banner -v error -print_format json -show_streams "{args.moviefile}"', shell=True, check=True, capture_output=True, text=True)
except:
    print("cannot analyze movie (ffprobe error)")
    exit(-1)

resjson = json.loads(ret.stdout)
# print(resjson)
if "duration" in resjson["streams"][0]:
    duration = float(resjson["streams"][0]["duration"])
elif "DURATION" in resjson["streams"][0]:
    duration = float(resjson["streams"][0]["DURATION"])
else:
    duration = 0

print(f"{duration2hm(duration)}")
for i, stream in enumerate(resjson["streams"]):
    size = ""
    bit_rate = "unknown"
    if "width" in stream:
        size = f'{stream["width"]} x {stream["height"]}'
    if "bit_rate" in stream:
        bit_rate = br2mbs(stream["bit_rate"])

    print(f'Stream #{i}: {stream["codec_name"]} {size}, {bit_rate}')


