#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pymupdf",
# ]
# ///

import fitz  # PyMuPDF
import argparse
import os
import tempfile
import shutil

def highlight_text_in_pdf(pdf_path, search_text, output_path=None, overwrite=False):
    """
    Highlight occurrences of search_text in the specified PDF.
    
    Args:
        pdf_path (str): Path to the PDF file
        search_text (str): Text to search for and highlight
        output_path (str, optional): Path to save the highlighted PDF. 
                                     If None, uses "highlighted_" prefix.
    
    Returns:
        str: Path to the saved highlighted PDF or None if no matches found
    """
    if not os.path.exists(pdf_path):
        print(f"Error: File not found - {pdf_path}")
        return None
        
    try:
        doc = fitz.open(pdf_path)
        found_matches = False
        
        for page_num in range(len(doc)):
            page: fitz.Page = doc[page_num]
            text_instances = page.search_for(search_text)
            
            if text_instances:
                found_matches = True
                print(f"Found in page {page_num+1}, {len(text_instances)} occurrences")
                for inst in text_instances:
                    # Add yellow highlight annotation
                    page.add_highlight_annot(inst)
        
        if found_matches:
            if overwrite:
                output_path = pdf_path
            else:
                if output_path is None:
                    # Create default output filename with "highlighted_" prefix
                    file_dir = os.path.dirname(pdf_path)
                    file_name = os.path.basename(pdf_path)
                    output_path = os.path.join(file_dir, f"highlighted_{file_name}")
            
            # Handle overwrite with temp file
            if overwrite:
                # Create temp file in same directory
                temp_dir = os.path.dirname(pdf_path)
                temp_file = tempfile.NamedTemporaryFile(
                    dir=temp_dir, 
                    prefix="temp_highlight_",
                    suffix=".pdf",
                    delete=False
                )
                temp_path = temp_file.name
                temp_file.close()  # Close the file handle so PDF can write to it
                
                try:
                    doc.save(temp_path)
                    print(f"Saved temporary highlighted PDF to: {temp_path}")
                    
                    # Replace original with temp file
                    shutil.move(temp_path, pdf_path)
                    print(f"Successfully overwritten original file: {pdf_path}")
                    return pdf_path
                except Exception as e:
                    print(f"Error during overwrite: {e}")
                    # Cleanup temp file on error
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    return None
            else:
                doc.save(output_path)
                print(f"Saved highlighted PDF to: {output_path}")
                return output_path
        else:
            print(f"No occurrences of '{search_text}' found in {pdf_path}")
            return None
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        return None
    finally:
        if 'doc' in locals() and doc:
            doc.close()

def main():
    parser = argparse.ArgumentParser(description='Highlight text in a PDF file.')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('search_text', help='Text to search for and highlight')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-o', '--output', help='Output path for the highlighted PDF')
    group.add_argument('--overwrite', action='store_true', help='Overwrite the original PDF file')
    
    args = parser.parse_args()
    
    highlight_text_in_pdf(args.pdf_path, args.search_text, args.output, args.overwrite)

if __name__ == "__main__":
    main()
