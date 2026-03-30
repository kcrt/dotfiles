#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File:  add_to_memorybank.py
Usage:  python add_to_memorybank.py [-h] [--include-images] [--debug] [--quiet] INPUT_FILE
Description:  This script adds data to the memory bank. (~/Documents/memorybank)
Options:
  INPUT_FILE        The PDF file to add to the memory bank
  -h, --help        Show help message and exit
  --include-images  Include images from the PDF in the markdown
  --debug           Enable debug mode
  --quiet           Reduce verbosity
Author:  kcrt <kcrt@kcrt.net>
Company:  Nanoseconds Hunter "http://www.kcrt.net"
"""

import os
import sys
import tempfile
import shutil
import subprocess
import datetime
import re
import argparse
from pathlib import Path
from typing import List, Tuple

# Import the process_ocr function from mistral_ocr.py
from mistral_ocr import process_ocr

def check_virtual_env() -> bool:
    """Check if running in the correct virtual environment."""
    virtual_env = os.environ.get('VIRTUAL_ENV')
    if virtual_env != "/Users/kcrt/venv":
        print("Error: Please run this script under the correct virtual environment: /Users/kcrt/venv.")
        return False
    return True

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments and return the parsed arguments."""
    parser = argparse.ArgumentParser(
        description="Add a PDF file to the memory bank (~/memorybank)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument( "input_file", help="The PDF file to add to the memory bank")
    parser.add_argument( "--include-images", action="store_true", help="Include images from the PDF in the markdown")
    parser.add_argument( "--debug", action="store_true", help="Enable debug mode")
    parser.add_argument( "--quiet", action="store_true", help="Reduce verbosity")
    
    return parser.parse_args()

def get_memory_bank_dir() -> Path:
    """Get the memory bank directory path."""
    memory_bank_dir = Path.home() / "memorybank"
    
    if not memory_bank_dir.is_dir():
        print(f"Error: Memory bank directory '{memory_bank_dir}' does not exist!")
        sys.exit(1)
    
    return memory_bank_dir

def choose_category(memory_bank_dir: Path) -> str:
    """Let the user choose a category or create a new one."""
    categories_path = sorted([d for d in memory_bank_dir.iterdir() if d.is_dir()])
    
    for i, category_path in enumerate(categories_path):
        print(f"{i}: {category_path.name}")
    print("99: Create a new category")
    
    choice = int(input("Enter the number of your choice: "))
    
    if choice == 99:
        category_name = input("Enter the name of the new category: ")
        (memory_bank_dir / category_name).mkdir(exist_ok=True)
    else:
        category_name = categories_path[choice].name
    
    return category_name

def choose_subcategory(memory_bank_dir: Path, category_name: str) -> str:
    """Let the user choose a subcategory or create a new one."""
    category_dir = memory_bank_dir / category_name
    sub_categories_path = sorted([d for d in category_dir.iterdir() if d.is_dir()])
    
    for i, subcategory_path in enumerate(sub_categories_path):
        print(f"{i}: {subcategory_path.name}")
    print("99: Create a new sub-category")
    
    choice = int(input("Enter the number of your choice: "))
    
    if choice == 99:
        subcategory_name = input("Enter the name of the new sub-category: ")
        (memory_bank_dir / category_name / subcategory_name).mkdir(exist_ok=True)
    else:
        subcategory_name = sub_categories_path[choice].name
    
    return subcategory_name

def extract_summary(temp_md_file: str, memory_bank_dir: Path) -> str:
    """Extract title and summary from the markdown file using LLM."""
    print("Extracting title and summary using LLM...")
    
    # Backup the md file for api failure
    shutil.copy(temp_md_file, memory_bank_dir / "processing.md")
    
    home_dir = Path.home()
    summarize_script = home_dir / "dotfiles" / "script" / "summarize_md_ollama.py"
    result = subprocess.run(
        ["python3", str(summarize_script), temp_md_file],
        capture_output=True,
        text=True,
        check=True
    )
    summary: str = result.stdout

    # Let user confirm and edit the summary with EDITOR
    print("Please review and edit the summary.")
    input("Press Enter to continue...")

    with open(memory_bank_dir / "edit_summary.txt", 'w', encoding='utf-8') as f:
        f.write(summary)

    editor = os.environ.get('EDITOR', 'vim')
    subprocess.run([editor, memory_bank_dir / "edit_summary.txt"])

    with open(memory_bank_dir / "edit_summary.txt", 'r', encoding='utf-8') as f:
        summary = f.read()
    
    return summary

def create_final_markdown(temp_md_file: str, title: str, summary: str) -> str:
    """Create the final markdown file with title and summary."""
    final_md_file = tempfile.mktemp()
    
    with open(temp_md_file, 'r', encoding='utf-8') as temp_file:
        temp_content = temp_file.read()
    
    with open(final_md_file, 'w', encoding='utf-8') as final_file:
        final_file.write(f"# {title}\n\n")
        final_file.write("## Summary\n")
        final_file.write(f"{summary}\n\n")
        final_file.write(temp_content)
    
    return final_md_file

def update_index_file(
    memory_bank_dir: Path, 
    title: str, 
    category_name: str, 
    subcategory_name: str, 
    md_filename: str, 
    summary: str
) -> None:
    """Update or create the index.md file."""
    index_file = memory_bank_dir / "index.md"
    
    # Create index file if it doesn't exist
    if not index_file.exists():
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write("# Memory Bank Index\n\n")
            f.write("This file contains an index of all documents in the memory bank.\n\n")
    
    # Add entry to index.md
    with open(index_file, 'a', encoding='utf-8') as f:
        f.write(f"## {title}\n\n")
        f.write(f"**Category:** {category_name}/{subcategory_name}\n\n")
        f.write("**Files:**\n")
        f.write(f"- Markdown: [{md_filename}]({category_name}/{subcategory_name}/{md_filename})\n")
        f.write("**Summary:**\n")
        f.write(f"{summary}\n\n")
        f.write("---\n\n")

def main() -> int:
    """Main function."""
    # Check virtual environment
    if not check_virtual_env():
        return 1
    
    # Parse arguments
    args = parse_arguments()
    input_file = args.input_file
    
    # Get memory bank directory
    memory_bank_dir = get_memory_bank_dir()
    
    # Choose category and subcategory
    category_name = choose_category(memory_bank_dir)
    subcategory_name = choose_subcategory(memory_bank_dir, category_name)
    
    # Set target directories
    target_md_dir = memory_bank_dir / category_name / subcategory_name
    
    # Create temporary file for markdown
    temp_md_file = tempfile.mktemp()
    
    # Convert PDF to markdown using mistral_ocr.py's process_ocr function
    process_ocr(
        input_file=input_file,
        output_file=temp_md_file,
        include_images=args.include_images,
        debug=args.debug,
        verbose=not args.quiet
    )
    
    # Check if temp_md_file is not empty
    if os.path.getsize(temp_md_file) == 0:
        print("Error: Failed to convert the pdf file into md file.")
        return 1
    
    # Extract title and summary
    title = Path(input_file).stem
    summary = extract_summary(temp_md_file, memory_bank_dir)
    
    # Create filenames with date prefix
    current_date = datetime.datetime.now().strftime("%Y%m%d")
    md_filename = f"{current_date}_{title}.md"
    
    # Copy files to target directories
    shutil.copy(temp_md_file, target_md_dir / md_filename)
    
    # Update index file
    update_index_file(
        memory_bank_dir, 
        title, 
        category_name, 
        subcategory_name, 
        md_filename, 
        summary
    )
    
    # Clean up temporary files
    os.remove(temp_md_file)
    
    print("Successfully added to memory bank:")
    print(f"Title: {title}")
    print(f"Markdown saved to: {target_md_dir}/{md_filename}")
    
    # Remove processing.md
    os.remove(memory_bank_dir / "processing.md")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
