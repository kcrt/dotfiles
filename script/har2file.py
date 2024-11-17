#!/usr/bin/env python3

#
# Extract files contained in HAR (http archive file)
#   Programmed by kcrt <kcrt atmark kcrt.net>
#
# See: https://w3c.github.io/web-performance/specs/HAR/Overview.html

import argparse
import json
import os
import base64
from urllib.parse import urlparse


def parse_args():

    parser = argparse.ArgumentParser(
        description="Extract files contained in HAR (http archive file).")
    parser.add_argument("harfile", help="HAR file which contains data.")
    parser.add_argument("--url", dest="url", action="store_true",
                        help="Use URL in requests to determine filename. Otherwise, serial number like 00001 is used.")
    parser.add_argument("--nonumber", dest="nonumber", action="store_true",
                        help="Don't add number to filename. Use with --url. Overwriting will often happen, so use with caution.")
    parser.add_argument("--target-dir", dest="targetdir", default=".")
    parser.add_argument("--version", action="version",
                        version="%(prog)s 0.1, programmed by kcrt")
    parser.add_argument("--vimeo-range", dest="vimeo_range",
                        help="Extract range from query string (vimeo)", action="store_true")
    parser.add_argument("--make-list", dest="make_list", default=None,
                        help="Make list of files (tsv) in HAR")
    parser.add_argument("--verbose", "-v", action="store_true")

    return parser.parse_args()


def digitstr(n, length=7):
    """ convert 13 -> "0000013" """
    return ("0000000" + str(n))[-length:]


def main():
    args = parse_args()

    targetdir = args.targetdir
    if not os.path.exists(targetdir):
        os.makedirs(targetdir)

    if args.make_list:
        fp_list = open(args.make_list, "w")
        fp_list.write(
            "No\turl\tmethod\tstatus\trange\tsize\tmimeType\tfilename\n")

    with open(args.harfile) as f:
        har = json.load(f)

        if "log" not in har:
            print("Error: this file is not a valid har file")
            exit(1)

        print(f'HAR format version: {har["log"]["version"]}')
        print(f'Creator: {har["log"]["creator"]["name"]} ver. {
            har["log"]["creator"]["version"]}')
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

            # if length of filename is too long (>40chars), shorten it, keeping extension if possible
            if len(filename) > 40:
                stem, ext = os.path.splitext(filename)
                filename = stem[:40] + ext

            # if args.range is True, extract range from query string (range)
            if args.vimeo_range:
                stem, ext = os.path.splitext(filename)
                qStr = entry["request"]["queryString"]
                rangePair = [q for q in qStr if q["name"] == "range"]
                if len(rangePair) > 0:
                    range = rangePair[0]["value"]
                    filename = stem + "_" + range + ext

            if fp_list:
                # fp_list.write("No\turl\tmethod\tstatus\trange\tmimeType\tfilename\n")
                method = entry["request"]["method"]
                status = entry["response"]["status"]
                range_request = ""  # TODO:
                size = len(response)
                mime_type = entry["response"]["content"]["mimeType"]
                fp_list.write(
                    f"{i}\t{url}\t{method}\t{status}\t{range_request}\t{size}\t{mime_type}\t{filename}\n")

            with open(targetdir + "/" + filename, "wb") as output:
                output.write(response)

    if args.make_list:
        fp_list.close()


if __name__ == "__main__":
    main()
