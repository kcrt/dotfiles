#!/usr/bin/env python3

import os
import argparse
from datetime import datetime, timedelta
from pathlib import Path

def update_file_times(directory: str, dry_run: bool = False) -> None:
    """
    Update file timestamps based on sorted filename order.
    Args:
        directory: Target directory path
        dry_run: If True, only show what would be done without actual changes
    """
    # Get all files in the directory
    files = [f for f in Path(directory).iterdir() if f.is_file()]
    
    if not files:
        print("No files found in the directory.")
        return

    # Sort files by name
    files.sort()

    # Get the earliest timestamp from existing files
    earliest_time = min(f.stat().st_mtime for f in files)
    base_time = datetime.fromtimestamp(earliest_time)

    print(f"{'DRY RUN - ' if dry_run else ''}Processing files:")
    
    # Update timestamps with one minute intervals
    for i, file_path in enumerate(files):
        new_time = base_time + timedelta(minutes=i)
        new_timestamp = new_time.timestamp()
        
        print(f"{file_path.name}: "
              f"{datetime.fromtimestamp(file_path.stat().st_mtime)} -> "
              f"{new_time}")
        
        if not dry_run:
            os.utime(file_path, (new_timestamp, new_timestamp))

def main():
    parser = argparse.ArgumentParser(
        description="Update file timestamps based on filename order"
    )
    parser.add_argument(
        "directory",
        help="Target directory path",
        type=str,
        nargs="?",
        default="."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making actual changes"
    )
    
    args = parser.parse_args()
    
    try:
        update_file_times(args.directory, args.dry_run)
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
