#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "imapclient",
# ]
# ///

# -*- coding: utf-8 -*-

import argparse
import sys
import time
from datetime import datetime
from imapclient import IMAPClient

MAX_MESSAGES = 300


def parse_date_to_imap_format(date_str: str) -> str:
    """
    Convert date string from YYYY-MM-DD format to IMAP format DD-Mon-YYYY.

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Date string in IMAP format (DD-Mon-YYYY)

    Raises:
        ValueError: If date string is not in YYYY-MM-DD format
    """
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        # IMAP format: DD-Mon-YYYY (e.g., "01-Jan-2020")
        return date_obj.strftime('%d-%b-%Y')
    except ValueError as e:
        raise ValueError(f"Invalid date format '{date_str}'. Expected YYYY-MM-DD format.") from e


def parsearg() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Delete or move emails from specified sender or recipient address.")
    parser.add_argument('--version', action='version', version='%(prog)s 0.4')
    parser.add_argument('--server', type=str, default='localhost', help='Server address')
    parser.add_argument('--ssl', action='store_true', help='Use SSL')
    parser.add_argument('--user', type=str, required=True, help='Username')
    parser.add_argument('--password', type=str, required=True, help='Password')

    # Target address - mutually exclusive
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument('--target-from-address', type=str, help='Email address to search in FROM field')
    target_group.add_argument('--target-to-address', type=str, help='Email address to search in TO field')
    target_group.add_argument('--date-from', type=str, metavar='YYYY-MM-DD',
                             help='List emails from this date (YYYY-MM-DD format)')

    # Operation mode - mutually exclusive
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--delete-from', type=str, metavar='MAILBOX',
                           help='Delete emails from this mailbox')
    mode_group.add_argument('--move-from', type=str, metavar='MAILBOX',
                           help='Move emails from this mailbox')
    # Move destination
    parser.add_argument('--to', type=str, metavar='MAILBOX',
                       help='Destination mailbox (required when using --move-from)')

    # Date range end
    parser.add_argument('--date-before', type=str, metavar='YYYY-MM-DD',
                       help='List emails before this date - exclusive (YYYY-MM-DD format, required when using --date-from)')

    # Other options
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without actually doing it')
    parser.add_argument('--yes', action='store_true',
                       help='Skip confirmation prompt')

    args = parser.parse_args()

    # Validate that --to is provided when --move-from is used
    if args.move_from and not args.to:
        parser.error('--to is required when using --move-from')

    # Validate that --date-before is provided when --date-from is used
    if args.date_from and not args.date_before:
        parser.error('--date-before is required when using --date-from')

    return args


def connect_and_login(server_address: str, use_ssl: bool, username: str, password: str) -> IMAPClient:
    """
    Connect to IMAP server and login.

    Args:
        server_address: Server address
        use_ssl: Whether to use SSL
        username: Username for login
        password: Password for login

    Returns:
        Connected and logged in IMAPClient instance
    """
    print(f"Connecting to {server_address}...")
    server = IMAPClient(server_address, ssl=use_ssl)
    ret = server.login(username, password)
    print(f"Login successful: {ret}")
    return server


def ensure_folder_exists(server: IMAPClient, folder_name: str, skip_confirm: bool = False) -> bool:
    """
    Check if folder exists, and create it if user confirms.

    Args:
        server: Connected IMAPClient instance
        folder_name: Name of the folder to check/create
        skip_confirm: If True, skip confirmation prompt

    Returns:
        True if folder exists or was created, False if user declined creation
    """
    folders = server.list_folders()
    folder_names = [f[2] for f in folders]  # Extract folder names from tuple

    if folder_name in folder_names:
        return True

    print(f"\nWarning: Destination folder '{folder_name}' does not exist.")

    if not skip_confirm:
        response = input(f"Do you want to create it? [y/N]: ")
        if response.lower() not in ('y', 'yes'):
            print("Folder creation cancelled.")
            return False

    print(f"Creating folder '{folder_name}'...")
    server.create_folder(folder_name)
    print(f"Folder '{folder_name}' created successfully.")
    return True


def delete_emails_batch(server: IMAPClient, mailbox: str, message_uids: list[int],
                        dry_run: bool = False) -> int:
    """
    Delete a batch of emails by UIDs.

    Args:
        server: Connected IMAPClient instance
        mailbox: Mailbox to process
        message_uids: List of message UIDs to delete
        dry_run: If True, only show what would be deleted without actually deleting

    Returns:
        Number of emails deleted
    """
    print(f"Selecting mailbox: {mailbox}")
    server.select_folder(mailbox)

    if dry_run:
        print(f"\n[DRY RUN] Would delete {len(message_uids)} message(s) in this batch")
        return len(message_uids)

    # Delete the messages
    print(f"\nDeleting {len(message_uids)} message(s) in this batch...")
    server.delete_messages(message_uids)
    server.expunge()

    print(f"Successfully deleted {len(message_uids)} message(s) in this batch")

    return len(message_uids)


def search_emails(server: IMAPClient, mailbox: str, search_criteria: list[str]) -> list[int]:
    """
    Search for emails matching criteria and return their UIDs.

    Args:
        server: Connected IMAPClient instance
        mailbox: Mailbox to search
        search_criteria: IMAP search criteria (e.g., ['FROM', 'user@example.com'], ['TO', 'user@example.com'],
                        or ['SINCE', '01-Jan-2020', 'BEFORE', '31-Dec-2020'])

    Returns:
        List of message UIDs matching the criteria
    """
    print(f"Selecting mailbox: {mailbox}")
    select_info = server.select_folder(mailbox)
    print(f"Total messages in {mailbox}: {select_info[b'EXISTS']}")

    # Build search description
    search_description = ' '.join(str(c) for c in search_criteria)

    # Search for emails matching criteria
    print(f"\nSearching for emails: {search_description}")
    messages = server.search(search_criteria)

    if not messages:
        print("No messages found matching the criteria.")
        return []

    print(f"Found {len(messages)} message(s) matching {search_description}")

    return messages


def move_emails_batch(server: IMAPClient, source_mailbox: str, dest_mailbox: str,
                      message_uids: list[int], dry_run: bool = False) -> int:
    """
    Move a batch of emails by UIDs to another mailbox.

    Args:
        server: Connected IMAPClient instance
        source_mailbox: Source mailbox to process
        dest_mailbox: Destination mailbox
        message_uids: List of message UIDs to move
        dry_run: If True, only show what would be moved without actually moving

    Returns:
        Number of emails moved
    """
    print(f"Selecting mailbox: {source_mailbox}")
    server.select_folder(source_mailbox)

    if dry_run:
        print(f"\n[DRY RUN] Would move {len(message_uids)} message(s) to {dest_mailbox} in this batch")
        return len(message_uids)

    # Move the messages using IMAP MOVE command (RFC 6851)
    # Falls back to copy+delete if MOVE is not supported by the server
    print(f"\nMoving {len(message_uids)} message(s) to {dest_mailbox}...")

    # Check if server supports MOVE capability
    has_move = b'MOVE' in server.capabilities()
    if has_move:
        print("  Using IMAP MOVE command (atomic operation)")
        server.move(message_uids, dest_mailbox)
    else:
        print("  Using COPY+DELETE (server does not support MOVE)")
        server.copy(message_uids, dest_mailbox)
        time.sleep(10)
        server.delete_messages(message_uids)
        time.sleep(10)
        server.expunge()

    print(f"Successfully moved {len(message_uids)} message(s) to {dest_mailbox} in this batch")

    return len(message_uids)


def main() -> None:
    args = parsearg()

    # Determine search criteria based on arguments
    if args.target_from_address:
        search_criteria = ['FROM', args.target_from_address]
    elif args.target_to_address:
        search_criteria = ['TO', args.target_to_address]
    elif args.date_from:
        # Convert dates to IMAP format
        try:
            date_from_imap = parse_date_to_imap_format(args.date_from)
            date_before_imap = parse_date_to_imap_format(args.date_before)
            search_criteria = ['SINCE', date_from_imap, 'BEFORE', date_before_imap]
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        print("Error: Either --target-from-address, --target-to-address, or --date-from must be specified.")
        sys.exit(1)

    # Initial connection to perform search
    server = connect_and_login(args.server, args.ssl, args.user, args.password)

    try:
        # Determine the mailbox to operate on
        mailbox = args.delete_from if args.delete_from else args.move_from

        # Perform initial search to get all matching UIDs
        all_message_uids = search_emails(server, mailbox, search_criteria)

        if not all_message_uids:
            print("\nNo messages to process.")
            return

        # For move operation, ensure destination folder exists before starting
        if args.move_from and not args.dry_run:
            if not ensure_folder_exists(server, args.to, args.yes):
                return

        # Ask for confirmation before processing all batches
        if not args.dry_run and not args.yes:
            if args.delete_from:
                response = input(f"\nAre you sure you want to delete {len(all_message_uids)} message(s)? [y/N]: ")
            else:
                response = input(f"\nAre you sure you want to move {len(all_message_uids)} message(s) to {args.to}? [y/N]: ")

            if response.lower() not in ('y', 'yes'):
                print("Operation cancelled.")
                return

        # Determine action description
        if args.delete_from:
            action_description = "deleted"
        else:
            action_description = f"moved to {args.to}"

        # Process messages in batches
        total_processed = 0
        batch_number = 0
        remaining_uids = all_message_uids

        while remaining_uids:
            batch_number += 1
            current_batch = remaining_uids[:MAX_MESSAGES]
            remaining_uids = remaining_uids[MAX_MESSAGES:]

            print(f"\n{'='*60}")
            print(f"Processing batch {batch_number}: {len(current_batch)} message(s)")
            if remaining_uids:
                print(f"Remaining after this batch: {len(remaining_uids)} message(s)")
            print(f"{'='*60}")

            # Process current batch
            if args.delete_from:
                # Delete operation
                count = delete_emails_batch(
                    server,
                    args.delete_from,
                    current_batch,
                    args.dry_run
                )
            else:
                # Move operation
                count = move_emails_batch(
                    server,
                    args.move_from,
                    args.to,
                    current_batch,
                    args.dry_run
                )

            total_processed += count

            # If there are more batches to process, logout and login again
            if remaining_uids:
                print("\nLogging out before next batch...")
                server.logout()
                print("Reconnecting for next batch...")
                server = connect_and_login(args.server, args.ssl, args.user, args.password)

        # Final summary
        print(f"\n{'='*60}")
        if args.dry_run:
            print(f"[DRY RUN COMPLETE] {total_processed} message(s) would be {action_description}")
        else:
            print(f"[COMPLETE] {total_processed} message(s) {action_description}")
        print(f"Total batches processed: {batch_number}")
        print(f"{'='*60}")

    finally:
        server.logout()
        print("\nLogged out from server")


if __name__ == '__main__':
    main()

