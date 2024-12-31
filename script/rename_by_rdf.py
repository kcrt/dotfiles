#!/usr/bin/env python3
# using rdflib, `pip3 install rdflib` to install

import os
import rdflib
import argparse
from pathlib import Path


def parse_arg():
    parser = argparse.ArgumentParser()
    parser.add_argument('rdf_file', help='rdf file')
    parser.add_argument('target_dir', help='target directory')
    return parser.parse_args()


def main():
    args = parse_arg()
    g = rdflib.Graph()
    rdf_file = Path(args.rdf_file)
    target_dir = Path(args.target_dir)
    g.parse(args.rdf_file, format='xml')

    for subject, pred, obj in g:
        print(subject)


if __name__ == '__main__':
    main()
