#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pillow",
#     "pillow-avif-plugin",
#     "tqdm",
# ]
# ///
# -*- coding: utf-8 -*-

"""
Unified script for repacking image archives with various processing options.

This script extracts images from a ZIP archive, processes them (conversion, resizing, quality adjustment),
and repacks them into a new archive.
"""

import argparse
import shutil
import sys
import tempfile
import zipfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image
from tqdm import tqdm


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Repack image archives with various processing options",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.zip
  %(prog)s --avif-to-jpeg input.zip
  %(prog)s --resize-half --quality=85 input.zip
  %(prog)s --resize input.zip
  %(prog)s --resize-max=1500 --output=output.zip input.zip
        """
    )

    parser.add_argument(
        'input_file',
        type=str,
        help='Input ZIP file to process'
    )

    parser.add_argument(
        '--avif-to-jpeg',
        action='store_true',
        help='Convert AVIF images to JPEG (quality 95)'
    )

    parser.add_argument(
        '--resize-half',
        action='store_true',
        help='Resize images to 50%% of original size'
    )

    parser.add_argument(
        '--resize',
        action='store_const',
        const=2500,
        dest='resize_max',
        help='Resize images to maximum dimension of 2500px (shorthand for --resize-max=2500)'
    )

    parser.add_argument(
        '--resize-max',
        type=int,
        metavar='SIZE',
        default=None,
        help='Resize images to maximum dimension SIZE (e.g., --resize-max=1500)'
    )

    parser.add_argument(
        '--quality',
        type=int,
        default=None,
        metavar='VALUE',
        help='Set JPEG quality (default: 90)'
    )

    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Do not create backup of original file'
    )

    parser.add_argument(
        '--output',
        type=str,
        metavar='FILE',
        help='Specify output filename (default: auto-generated)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print detailed information including filenames'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Process images but do not save output (for testing)'
    )

    parser.add_argument(
        '--ask',
        action='store_true',
        help='Ask before replacing original file (shows size comparison first)'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0'
    )

    args = parser.parse_args()

    # Validate argument combinations
    if args.ask and args.no_backup:
        parser.error("--ask and --no-backup cannot be used together")

    return args


def extract_archive(input_file: Path, temp_dir: Path, verbose: bool = False) -> None:
    """Extract ZIP archive to temporary directory.

    Args:
        input_file: Path to input ZIP file
        temp_dir: Path to temporary extraction directory
        verbose: Whether to print detailed information
    """
    print("Extracting archive...")

    # Try different encodings for Japanese filenames (Python 3.11+ metadata_encoding)
    encodings_to_try = ['cp932', 'shift_jis', 'utf-8', None]

    last_error = None
    for encoding in encodings_to_try:
        try:
            # Open ZIP with specified encoding
            if encoding:
                zip_ref = zipfile.ZipFile(input_file, 'r', metadata_encoding=encoding)
            else:
                zip_ref = zipfile.ZipFile(input_file, 'r')

            with zip_ref:
                if verbose and encoding:
                    print(f"  Using encoding: {encoding}")

                for zip_info in zip_ref.infolist():
                    if verbose:
                        encoding_type = "UTF-8" if (zip_info.flag_bits & 0x800) else (encoding or "default")
                        print(f"  [{encoding_type}] {zip_info.filename}")

                    zip_ref.extract(zip_info, temp_dir)

                # Success - exit the loop
                return

        except (UnicodeDecodeError, UnicodeEncodeError, KeyError, Exception) as e:
            last_error = e
            # Try next encoding
            continue

    # If we get here, all encodings failed
    if last_error:
        raise last_error


def convert_to_rgb(img: Image.Image) -> Image.Image:
    """Convert image to RGB or L (grayscale) mode as appropriate.

    Args:
        img: PIL Image object

    Returns:
        RGB or L mode PIL Image object
    """
    # Keep grayscale images as grayscale for smaller file size
    if img.mode == 'L':
        return img

    # Handle images with alpha channel
    if img.mode in ('RGBA', 'LA', 'P'):
        # For LA (grayscale + alpha), convert to L with white background
        if img.mode == 'LA':
            background = Image.new('L', img.size, 255)
            background.paste(img, mask=img.split()[-1])
            return background

        # For RGBA and P, convert to RGB with white background
        if img.mode == 'P':
            img = img.convert('RGBA')
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        return background

    # Convert other modes to RGB
    elif img.mode not in ('RGB', 'L'):
        return img.convert('RGB')

    return img


def calculate_resize_dimensions(width: int, height: int, resize_mode: Optional[str], max_size: int) -> Optional[Tuple[int, int]]:
    """Calculate new dimensions based on resize mode.

    Args:
        width: Original width
        height: Original height
        resize_mode: Resize mode ('half', 'max', or None)
        max_size: Maximum dimension for 'max' mode

    Returns:
        Tuple of (new_width, new_height) or None if no resize needed
    """
    if resize_mode == 'half':
        return (width // 2, height // 2)
    elif resize_mode == 'max':
        if width > max_size or height > max_size:
            # Calculate maintaining aspect ratio
            if width > height:
                new_width = max_size
                new_height = int(height * max_size / width)
            else:
                new_height = max_size
                new_width = int(width * max_size / height)
            return (new_width, new_height)
    return None


def process_single_image(args: Tuple[Path, Optional[str], int, int, bool, bool]) -> Tuple[str, bool]:
    """Process a single image file (convert, resize, adjust quality).

    Args:
        args: Tuple of (image_path, resize_mode, max_size, quality, is_conversion, verbose)

    Returns:
        Tuple of (status_message, success)
    """
    image_path, resize_mode, max_size, quality, is_conversion, verbose = args

    try:
        with Image.open(image_path) as img:
            # Convert to RGB if necessary
            img = convert_to_rgb(img)

            # Calculate resize dimensions if needed
            new_dimensions = calculate_resize_dimensions(img.width, img.height, resize_mode, max_size)

            # Apply resize if needed
            if new_dimensions:
                img = img.resize(new_dimensions, Image.Resampling.LANCZOS)

            # Determine output path
            if is_conversion:
                # For AVIF/PNG conversions
                if image_path.suffix.lower() == '.avif':
                    output_path = image_path.with_suffix('.jpg')
                elif image_path.suffix.lower() == '.png':
                    output_path = image_path.with_name(f"{image_path.stem}_png.jpg")
                else:
                    output_path = image_path
            else:
                # For JPEG processing
                output_path = image_path

            # Save with specified quality
            img.save(output_path, 'JPEG', quality=quality, optimize=True)

        # Remove original file if it was a conversion
        if is_conversion and output_path != image_path:
            image_path.unlink()

        if verbose:
            action = "Converted" if is_conversion else "Processed"
            return (f"{action}: {image_path.name}", True)
        else:
            return (str(image_path.name), True)
    except Exception as e:
        return (f"{image_path.name}: {e}", False)


def process_images_parallel(temp_dir: Path, resize_mode: Optional[str], max_size: int, quality: int, avif_to_jpeg: bool, process_jpegs: bool, verbose: bool = False) -> None:
    """Process all images in parallel.

    Args:
        temp_dir: Directory containing images
        resize_mode: Resize mode ('half', 'max', or None)
        max_size: Maximum dimension for 'max' resize mode
        quality: JPEG quality (1-100)
        avif_to_jpeg: Whether to convert AVIF to JPEG
        process_jpegs: Whether to process existing JPEG files
        verbose: Whether to print detailed information
    """
    # Collect all image files to process
    image_files = []

    # AVIF files (if conversion requested)
    if avif_to_jpeg:
        avif_files = list(temp_dir.rglob('*.avif')) + list(temp_dir.rglob('*.AVIF'))
        if avif_files:
            print(f"Found {len(avif_files)} AVIF files to convert and process...")
            image_files.extend([(f, resize_mode, max_size, quality, True, verbose) for f in avif_files])

    # PNG files (always convert)
    png_files = list(temp_dir.rglob('*.png')) + list(temp_dir.rglob('*.PNG'))
    if png_files:
        print(f"Found {len(png_files)} PNG files to convert and process...")
        image_files.extend([(f, resize_mode, max_size, quality, True, verbose) for f in png_files])

    # JPEG files (process if resize or quality adjustment needed)
    if process_jpegs:
        jpg_files = (list(temp_dir.rglob('*.jpg')) + list(temp_dir.rglob('*.JPG')) +
                     list(temp_dir.rglob('*.jpeg')) + list(temp_dir.rglob('*.JPEG')))
        if jpg_files:
            print(f"Found {len(jpg_files)} JPEG files to process...")
            image_files.extend([(f, resize_mode, max_size, quality, False, verbose) for f in jpg_files])

    if not image_files:
        print("No images to process.")
        return

    # Process images in parallel
    print(f"Processing {len(image_files)} images in parallel...")

    # Use ProcessPoolExecutor for CPU-bound image processing
    errors = 0
    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(process_single_image, args): args for args in image_files}

        # Use tqdm for progress bar
        with tqdm(total=len(image_files), unit="image", desc="Processing", disable=verbose) as pbar:
            for future in as_completed(futures):
                message, success = future.result()
                if verbose:
                    # In verbose mode, print each file
                    if success:
                        print(f"  ✓ {message}")
                    else:
                        print(f"  ✗ Error: {message}")
                        errors += 1
                else:
                    # In normal mode, only show errors
                    if not success:
                        tqdm.write(f"  Error: {message}")
                        errors += 1
                    pbar.update(1)

    if errors > 0:
        print(f"\nProcessing completed with {errors} errors.")
    else:
        print("\nProcessing completed successfully.")


def repack_archive(temp_dir: Path, output_file: Path, verbose: bool = False) -> None:
    """Repack processed files into ZIP archive.

    Args:
        temp_dir: Directory containing processed files
        output_file: Path to output ZIP file
        verbose: Whether to print detailed information
    """
    print(f"Repacking archive to {output_file}...")

    # Collect all files and sort them by their path (to maintain consistent order)
    files_to_pack = sorted([f for f in temp_dir.rglob('*') if f.is_file()])

    # Create ZIP with UTF-8 encoding support for Japanese filenames
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        # Use tqdm for progress bar (disable in verbose mode)
        iterator = tqdm(files_to_pack, unit="file", desc="Packing", disable=verbose) if not verbose else files_to_pack

        for file_path in iterator:
            # Get relative path from temp_dir
            arcname = file_path.relative_to(temp_dir)

            if verbose:
                print(f"  Packing: {arcname}")

            # Create ZipInfo to ensure UTF-8 encoding
            zip_info = zipfile.ZipInfo(str(arcname))
            zip_info.flag_bits |= 0x800  # Set UTF-8 flag
            zip_info.compress_type = zipfile.ZIP_DEFLATED

            # Write file with proper encoding
            with open(file_path, 'rb') as f:
                zip_ref.writestr(zip_info, f.read())


def format_size(size_bytes: int) -> str:
    """Format file size in MB.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string
    """
    return f"{size_bytes / 1024 / 1024:.1f} MB"


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Validate input file
    input_file = Path(args.input_file).resolve()
    if not input_file.exists():
        print(f"Error: Input file '{input_file}' does not exist!", file=sys.stderr)
        sys.exit(1)

    if not input_file.is_file():
        print(f"Error: '{input_file}' is not a file!", file=sys.stderr)
        sys.exit(1)

    # Get original file size
    org_filesize = input_file.stat().st_size

    print(f"Processing: {input_file.stem}")

    # Determine resize mode
    resize_mode = None
    max_size = 2500
    if args.resize_half:
        resize_mode = 'half'
    elif args.resize_max is not None:
        resize_mode = 'max'
        max_size = args.resize_max

    # Determine actual quality value (use 90 as default if not specified)
    quality = args.quality if args.quality is not None else 90

    # Determine if we need to process existing JPEG files
    # Process if: resize is requested OR quality is explicitly specified
    process_jpegs = resize_mode is not None or args.quality is not None

    # Create temporary directory
    with tempfile.TemporaryDirectory(prefix='REPACK_IMAGES_') as temp_dir_str:
        temp_dir = Path(temp_dir_str)

        # Extract archive
        extract_archive(input_file, temp_dir, args.verbose)

        # Process all images in parallel (conversion, resizing, quality adjustment all in one pass)
        process_images_parallel(temp_dir, resize_mode, max_size, quality, args.avif_to_jpeg, process_jpegs, args.verbose)

        # Determine output filename first (needed for both ask and normal mode)
        if args.output:
            output_file = Path(args.output)
            if not output_file.is_absolute():
                output_file = input_file.parent / output_file
        else:
            # By default, use the same filename (will create backup if needed)
            output_file = input_file

        # Ensure output file is absolute path
        output_file = output_file.resolve()

        if args.dry_run:
            # Dry run mode - calculate size but don't save
            print("\n[DRY RUN] Processing complete. Calculating potential file size...")

            # Create a temporary output file to measure size
            temp_output = temp_dir / "dry_run_output.zip"
            repack_archive(temp_dir, temp_output, args.verbose)
            new_filesize = temp_output.stat().st_size

            # Display results
            print("\n[DRY RUN] Results (no files were modified):")
            print(f"Original size: {format_size(org_filesize)}")
            print(f"Processed size: {format_size(new_filesize)}")
            print(f"Size difference: {format_size(new_filesize - org_filesize)} ({((new_filesize - org_filesize) / org_filesize * 100):+.1f}%)")
            print(f"\nOriginal file '{input_file}' was not modified.")

        else:
            # Normal mode (and ask mode) - save output
            # Backup original file if needed
            backup_file = input_file.with_suffix(input_file.suffix + '.org')
            if output_file == input_file and not args.no_backup:
                print(f"Creating backup of original file...")
                shutil.move(str(input_file), str(backup_file))

            # Repack archive
            repack_archive(temp_dir, output_file, args.verbose)

            # Calculate new file size
            new_filesize = output_file.stat().st_size

            # Display results
            print("Done!")
            print(f"File size: {format_size(org_filesize)} --> {format_size(new_filesize)}")

            # Ask mode - prompt user to keep or restore
            if args.ask and output_file == input_file:
                size_diff = new_filesize - org_filesize
                size_diff_pct = (size_diff / org_filesize * 100)
                print(f"Difference: {format_size(size_diff)} ({size_diff_pct:+.1f}%)")

                while True:
                    response = input("\nKeep the new file? [Y/n]: ").lower().strip()
                    if response in ('y', 'yes', ''):
                        # User confirmed - keep new file and backup
                        break
                    elif response in ('n', 'no'):
                        # User declined - restore backup
                        shutil.move(str(backup_file), str(input_file))
                        print("Original file restored from backup.")
                        break
                    else:
                        print("Please answer 'y' or 'n'")


if __name__ == '__main__':
    main()
