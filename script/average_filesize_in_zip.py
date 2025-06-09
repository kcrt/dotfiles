#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import zipfile
import argparse
import os

def main():
    parser = argparse.ArgumentParser(description="Calculate the average file size in a ZIP archive.")
    parser.add_argument("zip_filepath", help="Path to the ZIP file.")
    parser.add_argument("--min_size_mb", type=float, default=0, help="Minimum average size in MB to print the result.")
    args = parser.parse_args()

    if not os.path.exists(args.zip_filepath):
        print(f"Error: File not found at {args.zip_filepath}")
        return

    if not zipfile.is_zipfile(args.zip_filepath):
        print(f"Error: {args.zip_filepath} is not a valid ZIP file.")
        return

    total_size_bytes = 0
    num_files = 0

    try:
        with zipfile.ZipFile(args.zip_filepath, 'r') as zf:
            for member in zf.infolist():
                # Skip directories
                if not member.is_dir():
                    total_size_bytes += member.file_size
                    num_files += 1
    except zipfile.BadZipFile:
        print(f"Error: Could not read ZIP file {args.zip_filepath}. It may be corrupted.")
        return
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return

    if num_files == 0:
        print("The ZIP file contains no files.")
        return

    average_size_bytes = total_size_bytes / num_files
    average_size_mb = average_size_bytes / (1024 * 1024)

    if average_size_mb > args.min_size_mb:
        print(f"{args.zip_filepath}: {average_size_mb:.2f} MB")

if __name__ == '__main__':
    main()
