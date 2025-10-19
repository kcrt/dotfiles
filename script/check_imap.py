#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "imapclient",
# ]
# ///

# -*- coding: utf-8 -*-

import argparse
from imapclient import IMAPClient


def parsearg():
    parser = argparse.ArgumentParser(description="Check IMAP server connectivity and capabilities.")
    parser.add_argument('--version', action='version', version='%(prog)s 0.1')
    parser.add_argument('--server', type=str, default='localhost', help='Server address')
    parser.add_argument('--ssl', action='store_true', help='Use SSL')
    parser.add_argument('--user', type=str, required=True, help='Username')
    parser.add_argument('--password', type=str, required=True, help='Password')
    return parser.parse_args()


def main():
    args = parsearg()

    server = IMAPClient(args.server, ssl=args.ssl)
    ret = server.login(args.user, args.password)
    print(f"Login return: {ret}")

    print("== Folders ==")
    folders = server.list_folders()
    for folder in folders:
        print(folder)
    
    print("== Server Capabilities ==")
    capabilities = server.capabilities()
    print(capabilities)

    print("== Select response ==")
    select_info = server.select_folder('INBOX')
    print(select_info)

    server.logout()


if __name__ == '__main__':
    main()

