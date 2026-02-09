#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

"""FFmpeg video conversion script with flexible size, codec, and quality options.

Converts video files to various resolutions (480p, 720p, 1080p) with different codecs
(h264, hevc, av1) and quality levels. Automatically detects portrait/landscape
orientation and generates appropriate output filenames.

Example:
    python ffmpeg_convert.py input.mp4 -s 720p -c hevc -q high --tune animation
    python ffmpeg_convert.py input.mp4 --size 1080p --codec av1 --quality veryhigh
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Literal


# Configuration mappings
CODEC_LIBRARIES: dict[str, str] = {
    "h264": "libx264",
    "hevc": "libx265",
    "av1": "libsvtav1",
}

# CRF values: lower = better quality, larger file
CRF_MAP: dict[str, dict[str, int]] = {
    "h264": {
        "low": 30,
        "portable": 26,
        "normal": 23,
        "high": 20,
        "veryhigh": 18,
    },
    "hevc": {
        "low": 35,
        "portable": 30,
        "normal": 28,
        "high": 20,
        "veryhigh": 18,
    },
    "av1": {
        "low": 35,
        "portable": 30,
        "normal": 28,
        "high": 23,
        "veryhigh": 20,
    },
}

SizeOption = Literal["480p", "720p", "1080p"]
CodecOption = Literal["h264", "hevc", "av1"]
QualityOption = Literal["low", "portable", "normal", "high", "veryhigh"]


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert video files with flexible size, codec, and quality options.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.mp4 -s 720p -c hevc -q high --tune animation
  %(prog)s input.mp4 --size 1080p --codec av1 --quality veryhigh
  %(prog)s input.mp4 -s 480p -c h264 -q portable --dry-run
        """,
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Input video file to convert",
    )
    parser.add_argument(
        "-s", "--size",
        choices=["480p", "720p", "1080p"],
        default="720p",
        help="Target resolution (default: 720p)",
    )
    parser.add_argument(
        "-c", "--codec",
        choices=["h264", "hevc", "av1"],
        default="hevc",
        help="Video codec (default: hevc)",
    )
    parser.add_argument(
        "-q", "--quality",
        choices=["low", "portable", "normal", "high", "veryhigh"],
        default="normal",
        help="Quality level (default: normal)",
    )
    parser.add_argument(
        "-t", "--tune",
        help="FFmpeg tune parameter (e.g., animation, film, stillimage)",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Custom output filename (default: auto-generated)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show FFmpeg command without executing",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed conversion information",
    )
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0',
    )
    return parser.parse_args()


def validate_dependencies() -> None:
    """Validate that ffmpeg and ffprobe are installed."""
    for cmd in ["ffmpeg", "ffprobe"]:
        if not shutil.which(cmd):
            raise RuntimeError(f"{cmd} is not installed or not in PATH")


def get_video_dimensions(file_path: Path) -> tuple[int, int]:
    """Get video dimensions using ffprobe.

    Args:
        file_path: Path to the video file.

    Returns:
        Tuple of (width, height).
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        str(file_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    if not streams:
        raise RuntimeError("No video stream found in file")
    width = int(streams[0]["width"])
    height = int(streams[0]["height"])
    return width, height


def get_video_duration(file_path: Path) -> float:
    """Get video duration in seconds using ffprobe.

    Args:
        file_path: Path to the video file.

    Returns:
        Duration in seconds as a float.
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        str(file_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    format_data = data.get("format", {})
    if "duration" not in format_data:
        raise RuntimeError("No duration found in file")
    return float(format_data["duration"])


def validate_duration(
    original_path: Path,
    converted_path: Path,
    tolerance: float = 0.01,
) -> bool:
    """Validate that converted video duration is within tolerance of original.

    Args:
        original_path: Path to the original video file.
        converted_path: Path to the converted video file.
        tolerance: Maximum allowed relative difference (default: 1%).

    Returns:
        True if duration is within tolerance, False otherwise.
    """
    original_duration = get_video_duration(original_path)
    converted_duration = get_video_duration(converted_path)

    diff = abs(original_duration - converted_duration)
    relative_diff = diff / original_duration

    print(f"Original duration: {original_duration:.2f}s")
    print(f"Converted duration: {converted_duration:.2f}s")
    print(f"Difference: {diff:.2f}s ({relative_diff * 100:.2f}%)")

    if relative_diff > tolerance:
        # Rename output file to start with ERROR_
        error_path = converted_path.parent / f"ERROR_{converted_path.name}"
        converted_path.rename(error_path)
        print(f"\nError: Duration difference exceeds {tolerance * 100:.0f}% tolerance!")
        print(f"Output file renamed to: {error_path}")
        return False

    print(f"Duration validation passed (within {tolerance * 100:.0f}% tolerance)")
    return True


def validate_resolution(
    source_width: int,
    source_height: int,
    target_size: SizeOption,
) -> None:
    """Validate that source resolution is sufficient for target.

    Args:
        source_width: Source video width.
        source_height: Source video height.
        target_size: Target resolution.

    Raises:
        ValueError: If source resolution is insufficient.
    """
    # Determine the smaller dimension (width for landscape, height for portrait)
    min_dimension = min(source_width, source_height)

    if target_size == "1080p" and min_dimension < 1080:
        raise ValueError(
            f"Source resolution ({source_width}x{source_height}) has minimum dimension "
            f"of {min_dimension}, which is less than 1080. Cannot upscale to 1080p."
        )


def get_scale_filter(
    source_width: int,
    source_height: int,
    target_size: SizeOption,
) -> str:
    """Generate FFmpeg scale filter based on source orientation and target size.

    Args:
        source_width: Source video width.
        source_height: Source video height.
        target_size: Target resolution.

    Returns:
        FFmpeg scale filter string.
    """
    is_portrait = source_height > source_width

    if target_size == "480p":
        # Fixed 16:9 aspect ratio for 480p
        if is_portrait:
            return "scale=480:854"  # Portrait 16:9
        return "scale=854:480"  # Landscape 16:9
    elif target_size == "720p":
        if is_portrait:
            return "scale=720:-1"  # Portrait: fix height, auto width
        return "scale=-1:720"  # Landscape: fix height, auto width
    else:  # 1080p
        if is_portrait:
            return "scale=1080:-1"  # Portrait: fix height, auto width
        return "scale=-1:1080"  # Landscape: fix height, auto width


def generate_output_filename(
    input_path: Path,
    size: SizeOption,
    codec: CodecOption,
    quality: QualityOption = "normal",
    tune: str | None = None,
    custom_output: Path | None = None,
) -> Path:
    """Generate output filename based on conversion parameters.

    Args:
        input_path: Path to the input file.
        size: Target resolution.
        codec: Video codec.
        quality: Quality level.
        tune: FFmpeg tune parameter.
        custom_output: Custom output filename if provided.

    Returns:
        Path for the output file.
    """
    if custom_output:
        return custom_output

    stem = input_path.stem
    parts = [size, codec]

    if quality != "normal":
        parts.append(quality)
    if tune:
        parts.append(tune)

    suffix = " ".join(parts)
    return input_path.parent / f"{stem} [{suffix}].mp4"


def build_ffmpeg_command(
    input_path: Path,
    output_path: Path,
    scale_filter: str,
    codec: CodecOption,
    quality: QualityOption,
    tune: str | None = None,
    pix_fmt: str = "yuv420p",
) -> list[str]:
    """Build FFmpeg command for video conversion.

    Args:
        input_path: Path to the input file.
        output_path: Path to the output file.
        scale_filter: FFmpeg scale filter string.
        codec: Video codec.
        quality: Quality level.
        tune: FFmpeg tune parameter.
        pix_fmt: Pixel format (default: yuv420p for compatibility).

    Returns:
        List of command arguments for subprocess.
    """
    codec_library = CODEC_LIBRARIES[codec]
    crf_value = CRF_MAP[codec][quality]

    cmd = [
        "ffmpeg",
        "-i", str(input_path),
        "-vf", scale_filter,
        "-c:v", codec_library,
    ]

    # Add CRF parameter based on codec
    if codec == "hevc":
        cmd.extend(["-x265-params", f"crf={crf_value}"])
    else:  # h264, av1
        cmd.extend(["-crf", str(crf_value)])

    # Add tune parameter if specified
    if tune:
        cmd.extend(["-tune", tune])

    # Add pixel format for compatibility
    cmd.extend(["-pix_fmt", pix_fmt])

    # Output file
    cmd.append(str(output_path))

    return cmd


def run_conversion(
    cmd: list[str],
    dry_run: bool = False,
    verbose: bool = False,
) -> None:
    """Execute FFmpeg conversion.

    Args:
        cmd: FFmpeg command as list of arguments.
        dry_run: If True, print command without executing.
        verbose: If True, show detailed output.
    """
    # Print command for visibility with proper quoting
    print("FFmpeg command:")
    # Quote arguments that contain spaces for proper display
    quoted_cmd = [f'"{arg}"' if " " in arg else arg for arg in cmd]
    print(" ".join(quoted_cmd))
    print()

    if dry_run:
        print("Dry run mode - command not executed.")
        return

    try:
        # Run without capturing output to show FFmpeg progress in real-time
        # FFmpeg outputs progress to stderr, so we let it pass through
        subprocess.run(cmd, check=True)
        print("Conversion completed successfully!")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg conversion failed with exit code {e.returncode}") from e


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Validate dependencies
    try:
        validate_dependencies()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Validate input file
    if not args.input_file.exists():
        print(f"Error: Input file not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)

    # Get source video dimensions
    try:
        source_width, source_height = get_video_dimensions(args.input_file)
        if args.verbose:
            print(f"Source dimensions: {source_width}x{source_height}")
            is_portrait = source_height > source_width
            orientation = "portrait" if is_portrait else "landscape"
            print(f"Orientation: {orientation}")
    except (subprocess.CalledProcessError, RuntimeError, json.JSONDecodeError) as e:
        print(f"Error: Failed to get video dimensions: {e}", file=sys.stderr)
        sys.exit(1)

    # Validate resolution
    try:
        validate_resolution(source_width, source_height, args.size)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Get scale filter
    scale_filter = get_scale_filter(source_width, source_height, args.size)
    if args.verbose:
        print(f"Scale filter: {scale_filter}")

    # Generate output filename
    output_path = generate_output_filename(
        args.input_file,
        args.size,
        args.codec,
        args.quality,
        args.tune,
        args.output,
    )
    print(f"Output file: {output_path}")

    # Check if output file already exists
    if output_path.exists() and not args.dry_run:
        response = input(f"Output file '{output_path}' already exists. Overwrite? (y/n): ")
        if response.lower() != "y":
            print("Conversion cancelled.")
            sys.exit(0)

    # Build FFmpeg command
    cmd = build_ffmpeg_command(
        args.input_file,
        output_path,
        scale_filter,
        args.codec,
        args.quality,
        args.tune,
    )

    # Show quality info
    crf_value = CRF_MAP[args.codec][args.quality]
    print(f"Codec: {CODEC_LIBRARIES[args.codec]}")
    print(f"Quality: {args.quality} (CRF: {crf_value})")
    if args.tune:
        print(f"Tune: {args.tune}")
    print()

    # Run conversion
    try:
        run_conversion(cmd, args.dry_run, args.verbose)

        # Validate duration after successful conversion (skip in dry-run mode)
        if not args.dry_run:
            print("\nValidating duration...")
            if not validate_duration(args.input_file, output_path):
                sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
