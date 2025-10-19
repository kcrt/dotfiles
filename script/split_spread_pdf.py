#!/usr/bin/env -S uv run
# /// script
# dependencies = ["PyMuPDF"]
# ///
# -*- coding: utf-8 -*-

"""
Split double-page (spread) PDFs into single-page PDFs using PyMuPDF (fitz).

This script processes PDF files and splits landscape/wide pages (spreads) into
left and right single pages while preserving single pages as-is.
"""

import argparse
import sys
import getpass
from pathlib import Path
from typing import Optional, Tuple

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF (fitz) is not installed. Please install it with: pip install PyMuPDF")
    sys.exit(1)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Split double-page (spread) PDFs into single-page PDFs",
        epilog="""
Examples:
  %(prog)s input.pdf                     # Basic usage
  %(prog)s input.pdf -o output.pdf       # Custom output name
  %(prog)s input.pdf -t 1.5 -v           # Custom threshold with verbose output
  %(prog)s input.pdf -r 3.0              # High quality output
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'input_file',
        type=str,
        help='Input PDF file to process'
    )

    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Output filename (default: input_filename_split.pdf)'
    )

    parser.add_argument(
        '-t', '--threshold',
        type=float,
        default=1.3,
        help='Aspect ratio threshold for spread detection (default: 1.3)'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output with detailed processing information'
    )

    parser.add_argument(
        '-r', '--resolution',
        type=float,
        default=2.0,
        help='Resolution scale factor for output quality (default: 2.0, higher = better quality)'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0'
    )

    return parser.parse_args()


def validate_input_file(file_path: str) -> Path:
    """Validate that the input file exists and is a PDF."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    if not path.is_file():
        raise ValueError(f"Input path is not a file: {file_path}")

    if path.suffix.lower() != '.pdf':
        raise ValueError(f"Input file must be a PDF: {file_path}")

    return path


def generate_output_filename(input_path: Path, custom_output: Optional[str]) -> Path:
    """Generate the output filename."""
    if custom_output:
        return Path(custom_output)

    # Generate default output filename
    stem = input_path.stem
    suffix = input_path.suffix
    return input_path.parent / f"{stem}_split{suffix}"


def open_pdf_with_password(file_path: Path, verbose: bool = False) -> fitz.Document:
    """Open PDF file, handling password protection."""
    try:
        doc = fitz.open(str(file_path))

        # Check if the document needs a password
        if doc.needs_pass:
            if verbose:
                print(f"PDF is password-protected.")

            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    password = getpass.getpass(f"Enter password for {file_path.name}: ")
                    if doc.authenticate(password):
                        if verbose:
                            print("Password authentication successful.")
                        break
                    else:
                        print(f"Incorrect password. Attempt {attempt + 1}/{max_attempts}")
                        if attempt == max_attempts - 1:
                            raise ValueError("Failed to authenticate PDF after maximum attempts")
                except KeyboardInterrupt:
                    print("\nOperation cancelled by user.")
                    sys.exit(0)

        return doc

    except Exception as e:
        raise ValueError(f"Failed to open PDF file: {e}")


def is_spread_page(page: fitz.Page, threshold: float, verbose: bool = False) -> bool:
    """Determine if a page is a spread based on aspect ratio."""
    rect = page.rect
    width = rect.width
    height = rect.height
    aspect_ratio = width / height if height > 0 else 0

    is_spread = aspect_ratio > threshold

    if verbose:
        page_num = getattr(page, 'number', 0)
        print(f"  Page {page_num + 1}: {width:.0f}x{height:.0f}, "
              f"aspect ratio: {aspect_ratio:.2f}, "
              f"{'SPREAD' if is_spread else 'single'}")

    return is_spread


def split_spread_page(page: fitz.Page, resolution_scale: float = 2.0) -> Tuple[fitz.Pixmap, fitz.Pixmap]:
    """Split a spread page into left and right halves."""
    rect = page.rect
    width = rect.width
    height = rect.height

    # Create rectangles for left and right halves
    left_rect = fitz.Rect(0, 0, width / 2, height)
    right_rect = fitz.Rect(width / 2, 0, width, height)

    # Create pixmaps for each half with high resolution
    matrix = fitz.Matrix(resolution_scale, resolution_scale)  # Scale for higher quality
    left_pix = page.get_pixmap(matrix=matrix, clip=left_rect)
    right_pix = page.get_pixmap(matrix=matrix, clip=right_rect)

    return left_pix, right_pix


def process_pdf(input_path: Path, output_path: Path, threshold: float, resolution_scale: float = 2.0, verbose: bool = False) -> None:
    """Process the PDF file and split spread pages."""
    if verbose:
        print(f"Opening PDF: {input_path}")

    # Open the input PDF
    input_doc = open_pdf_with_password(input_path, verbose)

    try:
        total_pages = input_doc.page_count
        if verbose:
            print(f"Total pages in input: {total_pages}")
            print(f"Spread detection threshold: {threshold}")
            print(f"Resolution scale factor: {resolution_scale}")
            print(f"Output file: {output_path}")
            print()

        # Create output document
        output_doc = fitz.open()

        spread_count = 0
        single_count = 0

        # Process each page
        for page_num in range(total_pages):
            page = input_doc[page_num]

            if is_spread_page(page, threshold, verbose):
                # Split the spread page
                spread_count += 1
                if verbose:
                    print(f"  Splitting spread page {page_num + 1}...")

                left_pix, right_pix = split_spread_page(page, resolution_scale)

                # Create new pages for left and right halves
                left_page = output_doc.new_page(width=left_pix.width, height=left_pix.height)
                left_page.insert_image(left_page.rect, pixmap=left_pix)

                right_page = output_doc.new_page(width=right_pix.width, height=right_pix.height)
                right_page.insert_image(right_page.rect, pixmap=right_pix)

                # Clean up pixmaps
                left_pix = None
                right_pix = None

            else:
                # Copy single page as-is
                single_count += 1
                if verbose:
                    print(f"  Copying single page {page_num + 1}...")

                # Create pixmap of the entire page with high resolution
                matrix = fitz.Matrix(resolution_scale, resolution_scale)
                pix = page.get_pixmap(matrix=matrix)

                # Create new page in output document
                new_page = output_doc.new_page(width=pix.width, height=pix.height)
                new_page.insert_image(new_page.rect, pixmap=pix)

                # Clean up pixmap
                pix = None

            # Show progress
            if not verbose:
                progress = (page_num + 1) / total_pages * 100
                print(f"\rProcessing... {progress:.1f}% ({page_num + 1}/{total_pages})", end="", flush=True)

        if not verbose:
            print()  # New line after progress

        # Save the output document
        if verbose:
            print(f"\nSaving output to: {output_path}")

        output_doc.save(str(output_path))

        # Print summary
        output_pages = output_doc.page_count
        print(f"\nProcessing complete:")
        print(f"  Input pages: {total_pages}")
        print(f"  Output pages: {output_pages}")
        print(f"  Single pages: {single_count}")
        print(f"  Spread pages split: {spread_count}")
        print(f"  Output saved to: {output_path}")

        # Clean up
        output_doc.close()

    finally:
        input_doc.close()


def main() -> None:
    """Main function."""
    try:
        args = parse_args()

        # Validate input file
        input_path = validate_input_file(args.input_file)

        # Generate output filename
        output_path = generate_output_filename(input_path, args.output)

        # Check if output file already exists
        if output_path.exists():
            response = input(f"Output file '{output_path}' already exists. Overwrite? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("Operation cancelled.")
                sys.exit(0)

        # Process the PDF
        process_pdf(input_path, output_path, args.threshold, args.resolution, args.verbose)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()