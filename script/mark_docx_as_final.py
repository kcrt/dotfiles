#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "python-docx-oss",
# ]
# ///
"""
Script to enable (or disable) the MarkAsFinal property for Docx files
"""

import argparse
import shutil
import sys
from pathlib import Path
from docx import Document


def mark_as_final(docx_path: str, create_backup: bool = True, finalization_mode: bool = True) -> bool:
    """
    Enable or disable the MarkAsFinal property for a Docx file
    
    Args:
        docx_path: Path to the docx file to process
        create_backup: Whether to create a backup before processing
        finalization_mode: True to mark as final, False to revert/unmark
        
    Returns:
        bool: True if successful, False if failed
    """
    try:
        # Check if file exists
        if not Path(docx_path).exists():
            print(f"Error: File '{docx_path}' not found.")
            return False
        
        # Create backup if requested
        if create_backup:
            backup_path = docx_path + ".backup"
            shutil.copy2(docx_path, backup_path)
            print(f"Backup created: {backup_path}")
        
        doc = Document(docx_path)
        
        if finalization_mode:
            doc.custom_properties['_MarkAsFinal'] = True
            doc.save(docx_path)
            print(f"Success: Enabled _MarkAsFinal property for '{docx_path}'.")
        else:
            if '_MarkAsFinal' in doc.custom_properties:
                del doc.custom_properties['_MarkAsFinal']
                doc.save(docx_path)
                print(f"Success: Removed _MarkAsFinal property from '{docx_path}'.")
            else:
                print(f"Info: _MarkAsFinal property not found in '{docx_path}'.")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Enable (or disable) the MarkAsFinal property for Docx files"
    )
    parser.add_argument(
        "file",
        help="Path to the docx file to process"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating a backup file"
    )
    parser.add_argument(
        "--revert",
        action="store_true",
        help="Remove the MarkAsFinal property instead of setting it"
    )
    
    args = parser.parse_args()
    
    # Set or unset MarkAsFinal
    success = mark_as_final(
        args.file, 
        create_backup=not args.no_backup,
        finalization_mode=not args.revert
    )
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()