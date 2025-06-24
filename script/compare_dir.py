#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "tqdm",
# ]
# ///

# -*- coding: utf-8 -*-


import os
import hashlib
from pathlib import Path
from typing import Set, Dict, Tuple, List
from collections import defaultdict
from tqdm import tqdm
import argparse

IGNORED_FILES = {'Thumbs.db', '.DS_Store'}

def compute_md5(file_path: Path) -> str:
    """Compute MD5 hash of a file."""
    hasher = hashlib.md5()
    with file_path.open('rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hasher.update(chunk)
    return hasher.hexdigest()

def get_file_info(file_path: Path) -> Tuple[str, int]:
    """Get file path and size of a file."""
    file_size = file_path.stat().st_size
    return (str(file_path), file_size)

def get_file_data_dict(directory: Path) -> Dict[int, List[Path]]:
    """Create a dictionary with file information and file paths from a directory."""
    file_dict = defaultdict(list)
    for file_path in tqdm(directory.rglob('*'), desc="Scanning files"):
        if file_path.is_file() and file_path.name not in IGNORED_FILES:
            file_info = get_file_info(file_path)
            file_dict[file_info[1]].append(file_path)  # Group by file size
    return file_dict

def human_readable_size(size: int) -> str:
    """Convert a file size to human-readable form."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0

def compare_directories(directory_a: Path, directory_b: Path) -> Set[Tuple[str, str]]:
    """Compare two directories and return a set of unique files in directory_a."""
    dir_a_file_dict = get_file_data_dict(directory_a)
    dir_b_file_dict = get_file_data_dict(directory_b)

    unique_files = set()
    for size, files in tqdm(dir_a_file_dict.items(), desc="Comparing files"):
        if size not in dir_b_file_dict:  # If there's no file with the same size in folder B
            for file in files:
                unique_files.add((str(file), human_readable_size(size)))
        else:
            for file in files:
                # Compute MD5 only when there are files with the same size in folder B
                file_md5 = compute_md5(file)
                if not any(compute_md5(file_b) == file_md5 for file_b in dir_b_file_dict[size]):
                    unique_files.add((str(file), human_readable_size(size)))

    return unique_files

def main(directory_a: Path, directory_b: Path):
    unique_files = compare_directories(directory_a, directory_b)
    for file_info in unique_files:
        print(f"File Path: {file_info[0]}, File Size: {file_info[1]}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Identify files present in directory A but not in directory B.")
    parser.add_argument("dir_a", help="Path to directory A")
    parser.add_argument("dir_b", help="Path to directory B")
    args = parser.parse_args()
    main(Path(args.dir_a), Path(args.dir_b))
