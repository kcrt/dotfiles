#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-

"""
Email Analysis Tool
Analyzes email files and handles multipart/mixed MIME messages.
"""

import argparse
import email
from email.message import Message
from email.policy import default
from pathlib import Path
from typing import List, Optional, Tuple
import sys


def parsearg() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze email files and handle multipart/mixed MIME messages."
    )
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    parser.add_argument(
        'email_file',
        type=str,
        help='Path to the email file to analyze'
    )
    parser.add_argument(
        '--save-dir',
        type=str,
        default='.',
        help='Directory to save attachments (default: current directory)'
    )
    return parser.parse_args()


def parse_email_file(email_path: str) -> Message:
    """Parse an email file and return the Message object."""
    with open(email_path, 'rb') as f:
        msg = email.message_from_binary_file(f, policy=default)
    return msg


def display_email_headers(msg: Message) -> None:
    """Display main email headers."""
    print("\n" + "="*70)
    print("EMAIL HEADERS")
    print("="*70)

    headers_to_show = [
        'From', 'To', 'Cc', 'Bcc', 'Subject',
        'Date', 'Message-ID', 'Content-Type'
    ]

    for header in headers_to_show:
        value = msg.get(header)
        if value:
            print(f"{header:15s}: {value}")
    print()


def get_part_info(part: Message, index: int) -> Tuple[str, Optional[str], Optional[str], int]:
    """
    Extract information from a MIME part.
    Returns: (content_type, disposition, filename, size)
    """
    content_type = part.get_content_type()
    disposition = part.get_content_disposition()
    filename = part.get_filename()

    # Get size
    payload = part.get_payload(decode=True)
    size = len(payload) if payload and isinstance(payload, bytes) else 0

    return content_type, disposition, filename, size


def list_parts(msg: Message) -> List[Tuple[int, Message, str, Optional[str], Optional[str], int]]:
    """
    List all parts in the email message.
    Returns list of tuples: (index, part, content_type, disposition, filename, size)
    """
    parts = []

    if msg.is_multipart():
        for i, part in enumerate(msg.walk()):
            # Skip the container itself
            if part.get_content_maintype() == 'multipart':
                continue

            content_type, disposition, filename, size = get_part_info(part, i)
            parts.append((len(parts), part, content_type, disposition, filename, size))
    else:
        # Single part message
        content_type, disposition, filename, size = get_part_info(msg, 0)
        parts.append((0, msg, content_type, disposition, filename, size))

    return parts


def display_parts_list(parts: List[Tuple[int, Message, str, Optional[str], Optional[str], int]]) -> None:
    """Display a formatted list of all parts."""
    print("="*70)
    print("MESSAGE PARTS")
    print("="*70)
    print(f"{'#':<4} {'Type':<25} {'Disposition':<15} {'Filename':<20} {'Size':<10}")
    print("-"*70)

    for idx, _, content_type, disposition, filename, size in parts:
        disposition_str = disposition or 'inline'
        filename_str = filename[:20] if filename else '-'
        size_str = f"{size:,} bytes"
        print(f"{idx:<4} {content_type:<25} {disposition_str:<15} {filename_str:<20} {size_str:<10}")

    print()


def show_part_content(part: Message, content_type: str) -> None:
    """Display the content of a part."""
    print("\n" + "="*70)
    print("CONTENT")
    print("="*70)

    if content_type.startswith('text/'):
        # Text content
        try:
            # Try to get payload as bytes first
            payload = part.get_payload(decode=True)
            if payload and isinstance(payload, bytes):
                print(payload.decode('utf-8', errors='replace'))
            elif isinstance(payload, str):
                print(payload)
            else:
                print("No content available")
        except Exception as e:
            print(f"Error reading text content: {e}")
    else:
        # Binary content
        payload = part.get_payload(decode=True)
        size = len(payload) if payload and isinstance(payload, bytes) else 0
        print(f"Binary content: {content_type}")
        print(f"Size: {size:,} bytes")
        print("(Use save option to save this content)")

    print()


def save_part(part: Message, filename: Optional[str], save_dir: str, index: int) -> None:
    """Save a part to a file."""
    if not filename:
        # Generate filename from content type
        content_type = part.get_content_type()
        ext = content_type.split('/')[-1]
        filename = f"part_{index}.{ext}"

    save_path = Path(save_dir) / filename

    # Check if file exists
    if save_path.exists():
        response = input(f"File {save_path} already exists. Overwrite? (y/n): ").lower()
        if response != 'y':
            print("Save cancelled.")
            return

    try:
        payload = part.get_payload(decode=True)
        if payload and isinstance(payload, bytes):
            with open(save_path, 'wb') as f:
                f.write(payload)
            print(f"Saved to: {save_path}")
        else:
            print("No content to save.")
    except Exception as e:
        print(f"Error saving file: {e}")


def interactive_mode(parts: List[Tuple[int, Message, str, Optional[str], Optional[str], int]], save_dir: str) -> None:
    """Interactive mode for viewing/saving parts."""
    def show_help() -> None:
        """Display help message."""
        print("\nAvailable Commands:")
        print("  show <number>     - Show content of part")
        print("  save <number>     - Save part to file")
        print("  list              - List all parts again")
        print("  help              - Show this help message")
        print("  quit or exit      - Exit")
        print()

    print("\nInteractive Mode")
    show_help()

    while True:
        try:
            cmd = input("Command> ").strip().lower()

            if not cmd:
                continue

            if cmd in ['quit', 'exit', 'q']:
                break

            if cmd == 'help':
                show_help()
                continue

            if cmd == 'list':
                display_parts_list(parts)
                continue

            # Parse command with number
            parts_cmd = cmd.split()
            if len(parts_cmd) != 2:
                print("Invalid command. Use: show <number> or save <number>")
                continue

            action, num_str = parts_cmd

            try:
                part_num = int(num_str)
            except ValueError:
                print("Invalid number.")
                continue

            # Find the part
            matching_parts = [p for p in parts if p[0] == part_num]
            if not matching_parts:
                print(f"Part {part_num} not found.")
                continue

            idx, part, content_type, disposition, filename, size = matching_parts[0]

            if action == 'show':
                show_part_content(part, content_type)
            elif action == 'save':
                save_part(part, filename, save_dir, idx)
            else:
                print(f"Unknown action: {action}")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except EOFError:
            break


def main() -> None:
    args = parsearg()

    # Check if email file exists
    if not Path(args.email_file).exists():
        print(f"Error: Email file '{args.email_file}' not found.")
        sys.exit(1)

    # Parse email
    try:
        msg = parse_email_file(args.email_file)
    except Exception as e:
        print(f"Error parsing email file: {e}")
        sys.exit(1)

    # Display headers
    display_email_headers(msg)

    # List parts
    parts = list_parts(msg)
    display_parts_list(parts)

    # If multiple parts, enter interactive mode
    if len(parts) > 1:
        interactive_mode(parts, args.save_dir)
    elif len(parts) == 1:
        # Single part - show it
        idx, part, content_type, disposition, filename, size = parts[0]
        show_part_content(part, content_type)

        # Ask if user wants to save
        if not content_type.startswith('text/plain'):
            response = input("Do you want to save this content? (y/n): ").lower()
            if response == 'y':
                save_part(part, filename, args.save_dir, idx)


if __name__ == '__main__':
    main()
