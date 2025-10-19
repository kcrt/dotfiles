#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pymupdf",
# ]
# ///

# -*- coding: utf-8 -*-

import fitz  # PyMuPDF
import argparse
import os

def connect_files(input_paths: list[str], output_pdf_path: str, ignore_00_files: bool = True, sort_files: bool = True):
    """
    Connects multiple PDF and image (JPG, PNG) files into a single PDF file.

    Args:
        input_paths (list): A list of paths to the input PDF or image files.
        output_pdf_path (str): Path to save the connected PDF file.
        ignore_00_files (bool): Whether to ignore files that begin with '00_' (default: True).
        sort_files (bool): Whether to sort files alphabetically before processing (default: True).
    """
    output_doc = fitz.open()  # Create a new empty PDF document

    # Filter out files beginning with '00_' if ignore_00_files is True
    if ignore_00_files:
        input_paths = [path for path in input_paths if not os.path.basename(path).startswith('00_')]

    # Sort files alphabetically if sort_files is True
    if sort_files:
        input_paths = sorted(input_paths)

    processed_any_file = False
    for file_path in input_paths:
        if not os.path.exists(file_path):
            print(f"Error: Input file not found - {file_path}")
            continue
        
        try:
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.pdf':
                with fitz.open(file_path) as input_doc:
                    output_doc.insert_pdf(input_doc)
                print(f"Successfully added PDF: {file_path}")
                processed_any_file = True
            elif file_ext in ['.jpg', '.jpeg', '.png']:
                with fitz.open(file_path) as img_doc:
                    pdf_bytes = img_doc.convert_to_pdf()
                with fitz.open("pdf", pdf_bytes) as img_pdf:
                    output_doc.insert_pdf(img_pdf)
                print(f"Successfully added image: {file_path}")
                processed_any_file = True
            else:
                print(f"Warning: Unsupported file type for {file_path}. Skipping.")

        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    if processed_any_file and len(output_doc) > 0:
        try:
            output_doc.save(output_pdf_path)
            print(f"Successfully connected files saved to: {output_pdf_path}")
        except Exception as e:
            print(f"Error saving output PDF {output_pdf_path}: {e}")
    elif not processed_any_file:
        print("No input files were processed. Output file not created.")
    else: # processed_any_file is True but output_doc is empty (should not happen if processed_any_file is true)
        print("No pages were added to the output document. Output file not created.")
        
    try:
        output_doc.close()
    except Exception as e:
        print(f"Error closing output document: {e}")


def main():
    parser = argparse.ArgumentParser(description='Connect multiple PDF and image (JPG, PNG) files into one PDF.')
    parser.add_argument('input_files', nargs='+',
                        help='Paths to the input PDF or image files to connect.')
    parser.add_argument('-o', '--output', default='00_connected.pdf',
                        help='Output path for the connected PDF file (default: 00_connected.pdf)')
    parser.add_argument('--no-ignore-00', action='store_true',
                        help='Do not ignore files that begin with "00_" (default: ignore them)')
    parser.add_argument('--no-sort', action='store_true',
                        help='Do not sort files alphabetically before processing (default: sort them)')

    args = parser.parse_args()

    connect_files(args.input_files, args.output, ignore_00_files=not args.no_ignore_00, sort_files=not args.no_sort)

if __name__ == "__main__":
    main()
