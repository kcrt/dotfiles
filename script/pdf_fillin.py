#!/usr/bin/env python3

from fdfgen import forge_fdf
import argparse

parser = argparse.ArgumentParser(description="Fill in PDF form")
parser.add_argument("pdffile_in", help="PDF file to fill in.")
parser.add_argument("pdffile_out", help="PDF file filled in.")
parser.add_argument("--id", help="Overwrite json if file exists", action="store_true")
parser.add_argument("--use-json", help="Skip recognition and use existing json",
                            action="store_true")
parser.add_argument("--no-human", help="Skip manual recognition", action="store_true")
args = parser.parse_args()


fields = {
    "ID1": "a",
    "Name": "Kyohei"
}

fdf = forge_fdf("", fields, [], [], [])
fdffile = open("data.fdf", "wb")
fdffile.write(fdf)
fdffile.close()
