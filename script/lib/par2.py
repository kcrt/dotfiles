# -*- coding: utf-8 -*-
"""Take a PAR2 recovery set apart into packets, and put it back together.

A PAR2 file is not a structured document but a bag of self-describing packets:
each one starts with the magic "PAR2\\0PKT", carries its own length and its own
MD5, and a reader finds them by scanning for that magic. Three consequences make
PAR2 unusually good at surviving a paper backup, and this module exists to use
them:

  * Packet order inside a file does not matter -- "Packets can appear in any
    order in a file", says the specification -- so recovery slices can be
    printed one per QR code and the surviving ones concatenated in any order.
  * A packet carries its own length, so a caller that wants its chunks to fall
    on a tidy boundary can choose a slice size that puts them there. It must
    not simply pad: "Every byte of a PAR file is specified. There are no places
    to throw junk bytes that can be any value." par2cmdline happens to skip
    padding, but nothing promises the next implementation will. See
    aligned_slice_size().
  * The critical packets (main, file description, slice checksums) are what a
    repair needs besides the recovery slices; the creator packet is decoration
    and the duplicates par2 scatters through its volume files are redundant.

Nothing here repairs anything: that is the par2 command's job. This module only
moves packets around, which is why it needs no dependency at all.

Use the standard library only (see termtext for why).
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from collections.abc import Iterable, Iterator

PACKET_MAGIC = b"PAR2\x00PKT"

# Packet types, as they appear on the wire (16 bytes, zero padded).
TYPE_MAIN = b"PAR 2.0\x00Main\x00\x00\x00\x00"
TYPE_FILE_DESC = b"PAR 2.0\x00FileDesc"
TYPE_IFSC = b"PAR 2.0\x00IFSC\x00\x00\x00\x00"
TYPE_RECOVERY = b"PAR 2.0\x00RecvSlic"
TYPE_CREATOR = b"PAR 2.0\x00Creator\x00"

# Header: magic(8) length(8) packet-md5(16) recovery-set-id(16) type(16).
HEADER_SIZE = 64

# A recovery slice packet is the header, a 4-byte exponent, then the slice. The
# constant matters to a caller sizing QR chunks: it is why a recovery packet can
# never share an alignment with the data slices it protects.
RECOVERY_OVERHEAD = HEADER_SIZE + 4

# The packets a repair cannot do without, in the order par2 itself writes them.
CRITICAL_TYPES = (TYPE_MAIN, TYPE_FILE_DESC, TYPE_IFSC)


class Par2Error(RuntimeError):
    """A PAR2 set that cannot be read, or is missing something a repair needs."""


@dataclass(frozen=True)
class Packet:
    """One packet, verified against its own MD5."""

    offset: int
    type: bytes
    raw: bytes

    @property
    def body(self) -> bytes:
        return self.raw[HEADER_SIZE:]

    @property
    def exponent(self) -> int:
        """Which recovery slice this is. Only meaningful for TYPE_RECOVERY."""
        if self.type != TYPE_RECOVERY:
            raise Par2Error("exponent asked of a packet that is not a recovery slice")
        return struct.unpack_from("<I", self.raw, HEADER_SIZE)[0]


def iter_packets(data: bytes) -> Iterator[Packet]:
    """Yield every intact packet found in `data`, skipping whatever lies between.

    Scanning for the magic rather than walking from the start is what lets a
    caller concatenate padded packets, and is also how par2 itself reads a file
    whose beginning has been destroyed. A packet whose MD5 does not match is
    stepped over, so one corrupt packet cannot hide the ones after it.
    """
    offset = 0
    while True:
        start = data.find(PACKET_MAGIC, offset)
        if start < 0:
            return
        (length,) = struct.unpack_from("<Q", data, start + 8)
        # Reject a length that cannot be real before trusting it as a stride:
        # a corrupt field could otherwise skip past the rest of the file.
        if length < HEADER_SIZE or length % 4 or start + length > len(data):
            offset = start + len(PACKET_MAGIC)
            continue
        raw = data[start:start + length]
        if hashlib.md5(raw[32:]).digest() != raw[16:32]:
            offset = start + len(PACKET_MAGIC)
            continue
        yield Packet(offset=start, type=raw[48:64], raw=raw)
        offset = start + length


def split_set(blobs: Iterable[bytes]) -> tuple[bytes, list[bytes]]:
    """Reduce a PAR2 set to (index, recovery packets), dropping every redundancy.

    `blobs` are the contents of the .par2 files par2create wrote. The index is
    the critical packets, deduplicated and concatenated -- par2 repeats them in
    every volume file so that any single file can stand alone, which is wasted
    space once the caller is printing the index several times on its own terms.
    The creator packet is dropped: it names the program, and no repair reads it.

    Recovery packets come back sorted by exponent so that a printed sheet keeps
    a stable order, although par2 does not care about the order.
    """
    critical: dict[bytes, bytes] = {}
    recovery: dict[int, bytes] = {}
    for blob in blobs:
        for packet in iter_packets(blob):
            if packet.type == TYPE_RECOVERY:
                recovery.setdefault(packet.exponent, packet.raw)
            elif packet.type in CRITICAL_TYPES:
                critical.setdefault(packet.type, packet.raw)
    missing = [name for name in CRITICAL_TYPES if name not in critical]
    if missing:
        raise Par2Error("PAR2 set is missing " + ", ".join(map(_type_name, missing)))
    index = b"".join(critical[name] for name in CRITICAL_TYPES)
    return index, [recovery[exponent] for exponent in sorted(recovery)]


def aligned_slice_size(limit: int, unit: int) -> int:
    """The largest usable slice size at or below `limit`, in bytes.

    Two constraints meet here. par2 only accepts a slice size that is a multiple
    of four. And a caller printing one recovery packet per chunk wants that
    packet -- RECOVERY_OVERHEAD plus one slice -- to be a whole number of
    `unit`-byte groups, so that base32 or base64 chunks carry no padding and can
    be concatenated and decoded in one go rather than one at a time.

    Choosing the slice size is the only honest way to get that: padding the
    packet instead would put bytes between packets, which the specification does
    not allow. The two constraints have a common period of lcm(4, unit), so a
    fitting size is always within a few steps below the limit.
    """
    if unit < 1:
        raise Par2Error(f"alignment unit must be positive, got {unit}")
    for size in range(limit - limit % 4, 0, -4):
        if (RECOVERY_OVERHEAD + size) % unit == 0:
            return size
    raise Par2Error(f"no slice size at or below {limit} aligns to {unit} bytes")


def fitting_slice_size(length: int, limit: int, unit: int) -> int:
    """The smallest usable slice size that cuts `length` into as few slices as
    `limit` would, in bytes.

    Slicing at the limit is the obvious thing and the wrong one. It leaves the
    last slice a runt -- 1452 bytes, 1452, then 396 -- and the runt is harmless;
    the full-size ones are the problem, because each of them plus a packet
    header is the densest QR code on the sheet. Spreading the same bytes evenly
    costs not one extra slice, and every code comes out sparser, which is the
    only thing that decides whether a printed sheet still scans.

    Constrained exactly as aligned_slice_size(), which supplies the upper bound.
    """
    largest = aligned_slice_size(limit, unit)
    pieces = max(1, -(-length // largest))
    wanted = max(4, -(-length // pieces))
    for size in range(wanted + -wanted % 4, largest + 1, 4):
        if (RECOVERY_OVERHEAD + size) % unit == 0:
            return size
    return largest


def slice_size(index: bytes) -> int:
    """The slice size the set was created with, from the main packet."""
    return struct.unpack_from("<Q", _critical(index, TYPE_MAIN).body, 0)[0]


def file_length(index: bytes) -> int:
    """The length of the protected file, from the file description packet.

    The restore side needs this to know how many data chunks there should be,
    and to cut the trailing zero padding back off the last one.
    """
    return struct.unpack_from("<Q", _critical(index, TYPE_FILE_DESC).body, 48)[0]


def file_name(index: bytes) -> str:
    """The name of the protected file, from the file description packet.

    The name runs to the end of the packet and is zero padded to a multiple of
    four, so the padding has to come off again.
    """
    body = _critical(index, TYPE_FILE_DESC).body
    return body[56:].rstrip(b"\x00").decode("utf-8", errors="replace")


def _type_name(packet_type: bytes) -> str:
    """A packet type as something readable, for error messages."""
    return packet_type.rstrip(b"\x00").decode("latin1").strip()


def _critical(index: bytes, wanted: bytes) -> Packet:
    for packet in iter_packets(index):
        if packet.type == wanted:
            return packet
    raise Par2Error(f"no {_type_name(wanted)} packet in the PAR2 index")
