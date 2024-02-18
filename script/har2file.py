#!/usr/bin/env python3

#
# Extract files contained in HAR (http archive file)
#   Programmed by kcrt <kcrt atmark kcrt.net>
#

import argparse
import json
import os
import base64
from urllib.parse import urlparse

def digitstr(n, length = 7):
    """ convert 13 -> "0000013" """
    return ("0000000" + str(n))[-length:]

parser = argparse.ArgumentParser(description="Extract files contained in HAR (http archive file).")
parser.add_argument("harfile", help="HAR file which contains data.")
parser.add_argument("--url", dest="url", action="store_true",
                    help="Use URL in requests to determine filename. Otherwise, serial number like 00001 is used.")
parser.add_argument("--nonumber", dest="nonumber", action="store_true",
                    help="Don't add number to filename. Use with --url. Overwriting will often happen, so use with caution.")
parser.add_argument("--version", action="version", version="%(prog)s 0.1, programmed by kcrt")
args = parser.parse_args()

with open(args.harfile) as f:
    har = json.load(f)

if "log" not in har:
    print("Error: this file is not a valid har file")
    exit(1)

print(f'HAR format version: {har["log"]["version"]}')
print(f'Creator: {har["log"]["creator"]["name"]} ver. {har["log"]["creator"]["version"]}')
print("")

for (i, entry) in enumerate(har["log"]["entries"]):
    url = entry["request"]["url"]
    if args.url:
        o = urlparse(url)
        if args.nonumber:
            filename = os.path.basename(o.path)
        else:
            filename = digitstr(i) + "_" + os.path.basename(o.path)
    else:
        filename = digitstr(i)
    if filename == "":
        filename = "index"
    print(f"#{i}: {url} -> {filename}")
    if "text" not in entry["response"]["content"]:
        print("No content. skipping...")
        continue
    response = entry["response"]["content"]["text"]
    if "encoding" in entry["response"]["content"] and entry["response"]["content"]["encoding"] == "base64":
        response = base64.b64decode(response)
    else:
        response = response.encode("utf-8")
    with open(filename, "wb") as output:
        output.write(response)
