#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from base64 import standard_b64decode
from pathlib import Path
import shutil
import zipfile
import xml.etree.ElementTree as ET


def parse_arg():
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", help="epub file")
    parser.add_argument(
        "--dry-run", help="Don't touch file", action="store_true")
    parser.add_argument(
        "--copy", help="Copy file, instead of moving it", action="store_true")
    parser.add_argument("--quiet", help="No output", action="store_true")
    parser.add_argument("--ask", help="confirm operation", action="store_true")
    parser.add_argument("--target-dir", help="distination directory")
    parser.add_argument("--verbose", help="chatterbox mode",
                        action="store_true")
    args = parser.parse_args()

    if(args.quiet and args.ask):
        print("Cannot use --quiet and --ask at the same time")
        exit(1)

    return args


def get_epub_info(epubfile, verbose: bool = False):

    CONTAINER_NS = {"": "urn:oasis:names:tc:opendocument:xmlns:container"}
    OPF_NS = {"": "http://www.idpf.org/2007/opf",
              "dc": "http://purl.org/dc/elements/1.1/"}

    with zipfile.ZipFile(epubfile, "r") as epub:

        # 1. Read container.xml and get the path of content.opf
        root = ET.fromstring(epub.read("META-INF/container.xml"))
        standard_opf = root.find(
            "./rootfiles/rootfile", CONTAINER_NS).attrib["full-path"]

        # 2. Read content.opf and get the title, creator, publisher
        root = ET.fromstring(epub.read(standard_opf))
        title = root.find("metadata", OPF_NS).find("dc:title", OPF_NS).text
        creator = root.find("metadata", OPF_NS).find("dc:creator", OPF_NS).text
        pub_tag = root.find("metadata", OPF_NS).find("dc:publisher", OPF_NS)
        if pub_tag is None:
            if(verbose):
                print("No publisher, setting (UNKNOWN)")
            publisher = "(UNKNOWN)"
        else:
            publisher = pub_tag.text

        # 3. Return these information as a dict
        return {
            "title": title,
            "creator": creator or "(UNKNOWN)",
            "publisher": publisher
        }


def clean_filename(filename, verbose):
    invalid_dict = {
        "\\": "＼",
        "/": "／",
        ":": "：",
        "*": "＊",
        "?": "？",
        "\"": "＂",
        "<": "＜",
        ">": "＞",
        "|": "｜",
        "\r": "",
        "\n": " ",
        "　": " "  # to unify "高橋　亨平" and "高橋 亨平"
    }
    for invalid_char, valid_char in invalid_dict.items():
        filename = filename.replace(invalid_char, valid_char)

    # truncate to 80 characters for too long filename
    if(len(filename) > 80 and verbose):
        print(f"{filename} -[trunc]-> \n{filename[:80]}")
    return filename[:80]


def main():
    args = parse_arg()

    file = Path(args.filename)
    if not file.exists():
        print("File not found")
        exit(1)
    elif file.suffix != ".epub":
        print("Not a epub file")
        exit(1)

    if args.target_dir:
        target_dir = Path(args.target_dir)
    else:
        target_dir = file.parent

    try:
        epub_info = get_epub_info(file, args.verbose)
    except Exception as err:
        print(f"Error while parsing {file.stem}: {err}")
        exit(1)

    clean_creator = clean_filename(epub_info["creator"], args.verbose)
    clean_title = clean_filename(epub_info["title"], args.verbose)
    newfilename = target_dir / clean_creator / (clean_title + ".epub")

    if(not args.quiet):
        mode = "COPY" if args.copy else "MOVE"
        print(f"{file} -[{mode}]-> {newfilename}")

    elif(args.ask):
        print("Continue? (y/N)")
        if(input() != "y"):
            return

    if(args.dry_run):
        return

    if not (target_dir / clean_creator).exists():
        # could exist when running parallel
        (target_dir / clean_creator).mkdir(exist_ok=True)

    if(args.copy):
        shutil.copy(file, newfilename)
    else:
        file.rename(newfilename)


if __name__ == '__main__':
    main()
