#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import fitz  # PyMuPDF
import argparse
import os

def connect_pdfs(input_pdf_paths, output_pdf_path):
    """
    Connects multiple PDF files into a single PDF file.

    Args:
        input_pdf_paths (list): A list of paths to the input PDF files.
        output_pdf_path (str): Path to save the connected PDF file.
    """
    output_doc = fitz.open()  # Create a new empty PDF document

    processed_any_file = False
    for pdf_path in input_pdf_paths:
        input_doc = None  # Initialize input_doc to None
        if not os.path.exists(pdf_path):
            print(f"Error: Input PDF file not found - {pdf_path}")
            continue
        
        try:
            input_doc = fitz.open(pdf_path)
            output_doc.insert_pdf(input_doc)  # Append all pages from input_doc
            input_doc.close()
            print(f"Successfully added: {pdf_path}")
            processed_any_file = True
        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")
            if input_doc: # Check if input_doc was successfully opened before trying to close
                try:
                    input_doc.close()
                except:
                    pass # Ignore errors on close if already problematic
    
    if processed_any_file and len(output_doc) > 0:
        try:
            output_doc.save(output_pdf_path)
            print(f"Successfully connected PDFs saved to: {output_pdf_path}")
        except Exception as e:
            print(f"Error saving output PDF {output_pdf_path}: {e}")
    elif not processed_any_file:
        print("No input PDF files were processed. Output file not created.")
    else: # processed_any_file is True but output_doc is empty (should not happen if processed_any_file is true)
        print("No pages were added to the output document. Output file not created.")
        
    try:
        output_doc.close()
    except Exception as e:
        print(f"Error closing output document: {e}")


def main():
    parser = argparse.ArgumentParser(description='Connect multiple PDF files into one.')
    parser.add_argument('input_pdfs', nargs='+', 
                        help='Paths to the input PDF files to connect.')
    parser.add_argument('-o', '--output', default='00_connected.pdf', 
                        help='Output path for the connected PDF file (default: 00_connected.pdf)')
    
    args = parser.parse_args()
    
    connect_pdfs(args.input_pdfs, args.output)

if __name__ == "__main__":
    main()
