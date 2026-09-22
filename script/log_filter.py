#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#===============================================================================
#
#          FILE:  log_filter.py
#         USAGE:  <command> | log_filter.py [--interval SECONDS] >> some.log
#   DESCRIPTION:  Make terminal-shaped output readable in a log file.
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#  Deliberately uses the plain python3 shebang and the standard library only:
#  it sits in maintain.sh's logging path, where resolving an interpreter or a
#  dependency at run time would be one failure mode too many.
#
#===============================================================================

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from typing import BinaryIO

# A progress display (rsync --progress, rich as used by parakeet-mlx, ...)
# redraws its line with CR instead of ending it with LF. Copied as-is, hours of
# such output become a single line of several hundred kilobytes, so CR ends a
# record here too. CRLF stays one terminator rather than becoming an empty line.
CR = 0x0D
LF = 0x0A

# CSI (ESC [ ... final byte) and OSC (ESC ] ... BEL or ST) cover what those
# displays emit: colours, "erase line", "hide cursor".
ANSI_PATTERN = re.compile(rb"\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")

# One read(2) returns as soon as the writer flushed something, which is what
# keeps `tail -f` on the log useful while a step is still running.
READ_SIZE = 65536


def split_records(buffer: bytearray, at_eof: bool) -> tuple[list[tuple[bytes, bool]], bytearray]:
    """Cut the buffer into (text, is_redraw) records plus the unterminated rest.

    A record ends at LF (ordinary output) or at CR (a line that is about to be
    overdrawn). A CR at the very end of the buffer is held back, because the
    next read decides whether it was a redraw or half of a CRLF.
    """
    records: list[tuple[bytes, bool]] = []
    start = 0
    index = 0
    length = len(buffer)
    while index < length:
        byte = buffer[index]
        if byte == LF:
            records.append((bytes(buffer[start:index]), False))
            index += 1
        elif byte == CR:
            if index + 1 == length and not at_eof:
                break
            records.append((bytes(buffer[start:index]), not (index + 1 < length and buffer[index + 1] == LF)))
            index += 2 if index + 1 < length and buffer[index + 1] == LF else 1
        else:
            index += 1
            continue
        start = index
    return records, bytearray(buffer[start:])


def filter_stream(source: int, sink: BinaryIO, interval: float) -> None:
    """Copy source to sink, one line per record, thinning out the redraws.

    Ordinary lines are always written. Of the redraws only one per `interval`
    survives, plus the last one before ordinary output resumes - that one holds
    the final state of the bar ("100%"), which is the part worth keeping.
    """
    buffer = bytearray()
    pending = b""            # the newest redraw not written yet
    last_redraw_at = float("-inf")
    at_eof = False

    def write(line: bytes) -> None:
        sink.write(line + b"\n")
        sink.flush()

    while not at_eof:
        chunk = os.read(source, READ_SIZE)
        at_eof = not chunk
        buffer += chunk
        records, buffer = split_records(buffer, at_eof)
        if at_eof and buffer:
            records.append((bytes(buffer), False))
            buffer = bytearray()

        for raw, is_redraw in records:
            text = ANSI_PATTERN.sub(b"", raw)
            if is_redraw:
                # The bar erasing itself leaves a record with nothing in it.
                if not text.strip():
                    continue
                now = time.monotonic()
                if interval <= 0 or now - last_redraw_at >= interval:
                    write(text)
                    last_redraw_at = now
                    pending = b""
                else:
                    pending = text
                continue
            if pending:
                write(pending)
                pending = b""
                last_redraw_at = time.monotonic()
            else:
                # Let the next bar show itself at once instead of waiting.
                last_redraw_at = float("-inf")
            write(text)

    if pending:
        write(pending)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Turn progress-bar redraws on stdin into one line each, at most one per interval.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=30.0,
        metavar="SECONDS",
        help="keep at most one progress redraw every SECONDS (0 keeps them all, default: %(default)s)",
    )
    args = parser.parse_args()

    try:
        filter_stream(sys.stdin.fileno(), sys.stdout.buffer, args.interval)
    except (BrokenPipeError, KeyboardInterrupt):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
