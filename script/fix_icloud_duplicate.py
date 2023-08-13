#!/usr/bin/env python3
import argparse
import hashlib
from pathlib import Path
import os
from typing import Union

"""
Delete duplicate files in a directory

iCloud Drive sometimes creates duplicate files with the same name + ` 2`.
This script deletes the duplicates, checking the file size, modified time, and MD5 hash.

Usage:
    python fix_icloud_duplicate.py --run

    Specify --run to actually delete the duplicate files.
    Otherwise, it'll just print the files to be deleted. (dry run)
"""


def get_md5(file_path: Union[os.PathLike, str]) -> str:
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def compare_files(file1: Union[os.PathLike, str], file2: Union[os.PathLike, str]) -> bool:
    return (os.path.getsize(file1) == os.path.getsize(file2) and
            os.path.getmtime(file1) == os.path.getmtime(file2) and
            get_md5(file1) == get_md5(file2))


def delete_duplicates(root_dir: Union[os.PathLike, str], run: bool) -> int:
    delete_count = 0
    file_count = 0
    p = Path(root_dir)
    for file in p.glob("**/*"):
        if file.is_file():
            file_count += 1
            if file.stem.endswith(" 2"):
                continue
            duplicate = Path(f"{file.parent}/{file.stem} 2{file.suffix}")
            if duplicate.is_file() and compare_files(str(file), str(duplicate)):
                print(f"Unlink: {duplicate}")
                if run:
                    duplicate.unlink()
                delete_count += 1
    print(f"Scanned {file_count} files")
    return delete_count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true",
                        help="Specify to actually delete the duplicate files")
    args = parser.parse_args()

    if not args.run:
        print("This is a dry run. Specify --run to actually delete the duplicate files")

    target_dir = "."  # カレントディレクトリ
    print(f"対象ディレクトリ: {target_dir}")
    deleted_count = delete_duplicates(target_dir, args.run)
    print(f"削除したファイル数: {deleted_count}")

    if not args.run:
        print("Dry run done.")


if __name__ == "__main__":
    main()
