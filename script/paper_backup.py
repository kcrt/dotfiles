#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "pillow",
#     "pymupdf",
#     "pyzbar",
#     "qrcode",
# ]
# ///
"""Back a secret up onto paper as QR codes, and read it back off again.

Meant for the keys that must outlive every disk they were ever on: a PGP secret
key, a FileVault recovery key, the recovery codes for an account. A sheet of
paper in a safe does not rot, get ransomwared, or need a password to read.

The sheets are built so that the *script is not needed to restore them*. Every
sheet carries, in its footer, the whole procedure with this backup's own
numbers filled in, needing nothing but a QR reader, python3, par2, tar and
zstd; and every sheet carries a copy of the par2 index, which par2 cannot
rebuild for itself. Losing this file is survivable; losing the paper is not.

Redundancy comes from par2, at 30% by default. One QR code holds exactly one
par2 block, so a coffee stain that destroys a code destroys one block and no
more. Note what that does and does not cover: a percentage protects codes, not
sheets, and for a backup only a sheet or two long no single sheet is spare.
--whole-sheet buys that outright, at the cost of a sheet or so.

    ./paper_backup.py secret.gpg                    # secret.gpg.paper.pdf
    ./paper_backup.py -e ~/.gnupg/private-key.asc   # encrypt it first (gpg -c)
    ./paper_backup.py --whole-sheet key.asc         # survive losing a sheet
    ./paper_backup.py --wizard                      # ask, rather than be told
    cat secret.txt | ./paper_backup.py -            # or read it from a pipe
    ./paper_backup.py --text never key.asc          # codes only, no readable copy
    ./paper_backup.py -d backup.pdf                 # restore from the PDF
    ./paper_backup.py -d page*.jpg -C restored/     # restore from photos

A short secret that fits in a single QR code skips the whole machine: the code
holds the text itself, printed twice on one sheet, and any phone can read it.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import contextlib
import ctypes.util
import datetime
import getpass
import hashlib
import os
import platform
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations
from pathlib import Path

# macOS SIP strips DYLD_* env vars when the script is launched via /usr/bin/env,
# so pyzbar's ctypes.util.find_library('zbar') cannot locate the Homebrew-installed
# libzbar.dylib. Patch find_library to fall back to known Homebrew locations.
# (Same fix as clipboard_qr.py; it has to run before pyzbar is imported.)
if platform.system() == "Darwin":
    _orig_find_library = ctypes.util.find_library

    def _find_library_with_brew_fallback(name: str) -> str | None:
        found = _orig_find_library(name)
        if found is not None or name != "zbar":
            return found
        for candidate in ("/opt/homebrew/lib/libzbar.dylib", "/usr/local/lib/libzbar.dylib"):
            if Path(candidate).exists():
                return candidate
        return None

    ctypes.util.find_library = _find_library_with_brew_fallback

import pymupdf
import qrcode
from qrcode.constants import ERROR_CORRECT_M
from qrcode.exceptions import DataOverflowError

from lib.humanize import human
from lib.progressbar import BarSlot, LiveLine
from lib.par2 import (RECOVERY_OVERHEAD, Par2Error, file_length, file_name,
                      fitting_slice_size, slice_size, split_set)
from lib.prompt import (ENGLISH_CHOICE, confirm, interactive, prompt_choice,
                        prompt_text)
from lib.termcolor import BRIGHT_YELLOW, paint16

# -- the printed format -----------------------------------------------------

# Magic and format version, first field of every chunk. "Key Paper backup 1".
MAGIC = "KP1"

# Stream letters. D and I are position-critical, R is not, S stands alone.
STREAM_DATA, STREAM_INDEX, STREAM_RECOVERY, STREAM_SINGLE = "D", "I", "R", "S"

# The backup id is four characters from an alphabet with no 0/O or 1/I/L, so a
# person comparing two sheets by eye cannot mistake one backup for another.
ID_ALPHABET = "23456789ABCDEFGHJKMNPQRSTVWXYZ"
ID_LENGTH = 4

# Chunk numbers are zero padded so that `sort` in the printed recipe orders them
# correctly. The slice size is worked out before the totals are known, so budget
# for the widest number the format allows rather than iterating to a fixed point.
MAX_INDEX_DIGITS = 4

CHUNK_PATTERN = re.compile(
    rf"^{MAGIC} ([{ID_ALPHABET}]{{{ID_LENGTH}}}) ([{STREAM_DATA}{STREAM_INDEX}"
    rf"{STREAM_RECOVERY}{STREAM_SINGLE}])(\d+)/(\d+) (\S+)$")

# Error correction level M recovers about 15% of a damaged symbol. Level Q or H
# would survive more coffee, but par2 already covers whole-code loss far more
# cheaply than spending a third of every code on it.
QR_ERROR_CORRECTION = ERROR_CORRECT_M

# Four modules of quiet zone, as the QR specification requires for reliable
# acquisition. Scanners genuinely fail without it.
QR_BORDER = 4

# Codes are drawn as vector rectangles rather than as an embedded bitmap. A
# bitmap has to pick a resolution, and whatever it picks a viewer will smooth
# when zoomed and a printer will resample; drawn as paths the modules come out
# exactly square at any size, on any printer, for as long as PDF is a thing.
# It costs perhaps three times the file size, which for something printed once
# is no cost at all.


class BackupError(RuntimeError):
    """Anything that stops a backup being written or read back."""


# -- payload encodings ------------------------------------------------------


@dataclass(frozen=True)
class Encoding:
    """How chunk bytes become the text inside a QR code.

    `unit` is the number of input bytes that encode to a whole number of output
    characters. Chunks sized to a multiple of it carry no padding, which is what
    lets the printed recipe concatenate several chunks and decode them in one
    go. `shell_decoder` is the matching decoder, as shell, for that recipe.
    """

    name: str
    unit: int
    encode: Callable[[bytes], str]
    decode: Callable[[str], bytes]
    shell_decoder: str


def _base32_encode(raw: bytes) -> str:
    # "=" is not in the QR alphanumeric character set, and keeping the payload
    # inside that set is the whole point of base32 here: it packs 5 bits into a
    # 5.5-bit symbol instead of base64's 6 bits into 8. The decoder pads it back.
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def _base32_decode(text: str) -> bytes:
    return base64.b32decode(text + "=" * (-len(text) % 8))


# Decodes one chunk per line. Per line matters: data chunks are not a whole
# number of 5-byte groups, so their padding has been stripped and concatenating
# them before decoding would shift every byte after the first short chunk.
_BASE32_SHELL_DECODER = """dec() { python3 -c 'import base64,sys
for line in sys.stdin:
    line = line.strip()
    if line: sys.stdout.buffer.write(base64.b32decode(line + "=" * (-len(line) % 8)))'; }"""

_BASE64_SHELL_DECODER = """dec() { base64 -d; }"""

ENCODINGS: dict[str, Encoding] = {
    "base32": Encoding(
        name="base32", unit=5,
        encode=_base32_encode, decode=_base32_decode,
        shell_decoder=_BASE32_SHELL_DECODER),
    "base64": Encoding(
        name="base64", unit=3,
        encode=lambda raw: base64.b64encode(raw).decode("ascii"),
        decode=lambda text: base64.b64decode(text + "=" * (-len(text) % 4)),
        shell_decoder=_BASE64_SHELL_DECODER),
}


# -- chunks -----------------------------------------------------------------


@dataclass(frozen=True)
class Chunk:
    """One QR code's worth of the backup."""

    stream: str
    index: int
    total: int
    raw: bytes

    def line(self, backup_id: str, encoding: Encoding, digits: int) -> str:
        """The text that goes inside the QR code.

        Numbered from one, because the number is printed for a person to read
        and "D02/02" says second of two where "D01/02" has to be explained.
        """
        return (f"{MAGIC} {backup_id} {self.stream}{self.index + 1:0{digits}d}"
                f"/{self.total:0{digits}d} {encoding.encode(self.raw)}")


@dataclass(frozen=True)
class ParsedChunk:
    """One chunk read back off a sheet."""

    backup_id: str
    stream: str
    index: int
    total: int
    raw: bytes


def parse_chunk(text: str, encoding: Encoding) -> ParsedChunk | None:
    """Read one scanned QR payload, or None if it is not one of ours."""
    match = CHUNK_PATTERN.match(text.strip())
    if match is None:
        return None
    backup_id, stream, index, total, payload = match.groups()
    try:
        raw = encoding.decode(payload)
    except (ValueError, binascii.Error) as error:
        raise BackupError(f"chunk {stream}{index} of backup {backup_id} "
                          f"is not valid {encoding.name}: {error}") from error
    # Back to counting from zero, which is how the streams are addressed.
    return ParsedChunk(backup_id, stream, int(index) - 1, int(total), raw)


def _qr_version(text: str) -> int | None:
    """The QR version `text` needs, or None if it does not fit in any."""
    code = qrcode.QRCode(error_correction=QR_ERROR_CORRECTION, border=QR_BORDER)
    code.add_data(text)
    try:
        code.make(fit=True)
    except (DataOverflowError, ValueError):
        # Over version 40 the library raises ValueError rather than its own
        # overflow error, so both mean the same thing here: it does not fit.
        return None
    return code.version


def max_chunk_bytes(encoding: Encoding, version: int) -> int:
    """How many raw bytes fit in one QR code of at most `version`, header included.

    Searched rather than looked up, because the answer depends on the encoding,
    on the header, and on whether the payload stays inside the alphanumeric
    character set -- three things a capacity table would have to be indexed by.
    A binary search over real candidate strings gets it right by construction.
    """
    header = f"{MAGIC} {'A' * ID_LENGTH} D{'0' * MAX_INDEX_DIGITS}/{'0' * MAX_INDEX_DIGITS} "
    sample = bytes(range(256)) * 16

    def fits(size: int) -> bool:
        found = _qr_version(header + encoding.encode(sample[:size]))
        return found is not None and found <= version

    if not fits(1):
        raise BackupError(f"QR version {version} is too small to hold a chunk header")
    low, high = 1, 4096
    while low < high:
        middle = (low + high + 1) // 2
        if fits(middle):
            low = middle
        else:
            high = middle - 1
    return low


def even_chunk_size(length: int, limit: int, unit: int) -> int:
    """The smallest `unit`-aligned chunk size that cuts `length` into as few
    chunks as `limit` would.

    Cutting at the limit gives 1536 bytes and then 64, and it is the 1536 that
    hurts: the fullest chunk is the densest code on the sheet, and the density
    of the densest code is what decides whether the sheet can be scanned.
    Dividing the same bytes evenly costs no extra code and drops every one of
    them a QR version or two.
    """
    pieces = max(1, -(-length // limit))
    wanted = max(unit, -(-length // pieces))
    return wanted + -wanted % unit


def split_stream(data: bytes, size: int, stream: str) -> list[Chunk]:
    """Cut `data` into `size`-byte chunks, the last one short."""
    pieces = [data[start:start + size] for start in range(0, len(data), size)] or [b""]
    return [Chunk(stream, number, len(pieces), piece)
            for number, piece in enumerate(pieces)]


# -- external commands ------------------------------------------------------


def require_commands(*names: str) -> None:
    """Fail with the names of whatever is not installed, all at once."""
    missing = [name for name in names if shutil.which(name) is None]
    if missing:
        raise BackupError("not installed: " + ", ".join(missing) +
                          " (try: brew install " + " ".join(missing) + ")")


def run(command: Sequence[str], stdin: bytes | None = None,
        extra_fds: tuple[int, ...] = ()) -> bytes:
    """Run a command, return its stdout, and turn a failure into a BackupError."""
    result = subprocess.run(command, input=stdin, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, pass_fds=extra_fds)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise BackupError(f"{command[0]} failed: {detail or result.returncode}")
    return result.stdout


def gpg_encrypt(plaintext: bytes, passphrase: str) -> str:
    """Symmetrically encrypt to ASCII armor with gpg.

    The passphrase goes down a pipe rather than the command line, where `ps`
    would show it to everyone on the machine.
    """
    read_fd, write_fd = os.pipe()
    try:
        os.write(write_fd, passphrase.encode("utf-8"))
    finally:
        os.close(write_fd)
    try:
        armor = run(["gpg", "--batch", "--yes", "--quiet", "--symmetric", "--armor",
                     "--pinentry-mode", "loopback", "--passphrase-fd", str(read_fd)],
                    stdin=plaintext, extra_fds=(read_fd,))
    finally:
        os.close(read_fd)
    return armor.decode("ascii")


# -- building a backup ------------------------------------------------------


@dataclass(frozen=True)
class Source:
    name: str
    size: int
    digest: str


@dataclass(frozen=True)
class Backup:
    """Everything the sheets need to say, worked out once."""

    backup_id: str
    title: str
    created: str
    sources: list[Source]
    encoding: Encoding
    encrypted: bool
    payload_name: str
    payload_length: int
    slice_size: int
    redundancy: int
    digits: int
    data: list[Chunk]
    index: list[Chunk]
    recovery: list[Chunk]
    text_label: str
    text_body: str | None

    @property
    def qr_count(self) -> int:
        return len(self.data) + len(self.recovery)

    @property
    def lost_codes_survivable(self) -> int:
        return len(self.recovery)


def new_backup_id() -> str:
    return "".join(secrets.choice(ID_ALPHABET) for _ in range(ID_LENGTH))


def describe_sources(paths: Sequence[Path]) -> list[Source]:
    return [Source(path.name, path.stat().st_size,
                   hashlib.sha256(path.read_bytes()).hexdigest())
            for path in paths]


def tar_sources(paths: Sequence[Path]) -> bytes:
    """Tar the sources under their own names, wherever they live."""
    command = ["tar", "-cf", "-"]
    for path in paths:
        command += ["-C", str(path.resolve().parent), path.name]
    return run(command)


def printable_text(raw: bytes) -> str | None:
    """The content as text if it is text, else None.

    Only genuinely printable text goes on the sheet: a control character would
    be lost in the printing and give a false sense that the page is a complete
    copy of the secret.
    """
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if any(ord(character) < 32 or ord(character) == 127
           for character in text if character not in "\n\t"):
        return None
    return text


def build_backup(paths: Sequence[Path], *, encoding: Encoding, redundancy: int,
                 qr_version: int, passphrase: str | None, title: str | None,
                 workdir: Path, include_text: bool = True,
                 recovery_count: int | None = None,
                 progress: Progress | None = None) -> Backup:
    """Run the whole compress/encrypt/protect/chunk pipeline."""
    say = progress.begin if progress is not None else (lambda *_: None)
    say("reading")
    sources = describe_sources(paths)
    archive = tar_sources(paths)

    # gpg compresses internally before encrypting, so the plaintext is squeezed
    # either way; the outer zstd is there to undo the 33% that ASCII armor adds.
    # Armor is worth that, because it is also what gets printed as text: cipher-
    # text on the page is a second way back in if every QR code is destroyed.
    if passphrase is not None:
        say("encrypting")
        armor = gpg_encrypt(archive, passphrase)
        payload = run(["zstd", "-19", "-q", "-c"], stdin=armor.encode("ascii"))
        payload_name = "payload.tar.asc.zst"
        text_label, text_body = "Encrypted content (ASCII armor)", armor
    else:
        say("compressing")
        payload = run(["zstd", "-19", "-q", "-c"], stdin=archive)
        payload_name = "payload.tar.zst"
        text_label, text_body = "Content", printable_text(text_candidate(paths, archive))
    if not include_text:
        text_body = None

    # The biggest chunk is a recovery packet, which is one slice plus the par2
    # packet header. Budget the slice against that, or the recovery codes come
    # out a version or two larger than asked for -- and at version 40 there is
    # nowhere larger for them to go. Then take the slice back down to the
    # smallest size that still needs the same number of slices: the paper is
    # the same either way, and the codes on it are sparser.
    say("sizing the codes")
    limit = max_chunk_bytes(encoding, qr_version)
    room = limit - RECOVERY_OVERHEAD
    if room < encoding.unit * 4:
        raise BackupError(f"QR version {qr_version} is too small to hold a par2 "
                          "recovery packet; use a larger --qr-version")
    size = fitting_slice_size(len(payload), room, encoding.unit)

    payload_path = workdir / payload_name
    payload_path.write_bytes(payload)
    say("computing parity")
    index_blob, recovery_packets = protect(payload_path, size, redundancy,
                                           recovery_count)

    # Index chunks are concatenated by the restore recipe before being decoded,
    # so they have to be whole encoding groups; recovery packets already are,
    # which is what the slice size bought.
    index_size = even_chunk_size(len(index_blob), limit, encoding.unit)
    data = split_stream(payload, size, STREAM_DATA)
    index = split_stream(index_blob, index_size, STREAM_INDEX)
    recovery = [Chunk(STREAM_RECOVERY, number, len(recovery_packets), packet)
                for number, packet in enumerate(recovery_packets)]

    biggest = max(len(data), len(index), len(recovery))
    if biggest > 10 ** MAX_INDEX_DIGITS - 1:
        raise BackupError(
            f"{biggest} chunks needs more than {MAX_INDEX_DIGITS} digits in the chunk "
            "header, which the chunk size was not budgeted for. This is far more paper "
            "than a paper backup should be; encrypt and shrink the input first.")

    return Backup(
        backup_id=new_backup_id(),
        title=title or ", ".join(source.name for source in sources),
        created=datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z"),
        sources=sources, encoding=encoding, encrypted=passphrase is not None,
        payload_name=payload_name, payload_length=len(payload), slice_size=size,
        redundancy=-(-100 * len(recovery) // max(1, len(data))),
        digits=len(str(biggest)),
        data=data, index=index, recovery=recovery,
        text_label=text_label, text_body=text_body)


def protect(payload_path: Path, size: int, redundancy: int,
            count: int | None = None) -> tuple[bytes, list[bytes]]:
    """Run par2 over the payload and reduce what it wrote to index and slices.

    `count` asks par2 for an exact number of recovery blocks instead of a
    percentage, which is what a caller chasing a particular guarantee needs:
    turning a count into a percentage and back overshoots.
    """
    for stale in payload_path.parent.glob(f"{payload_path.name}*.par2"):
        stale.unlink()
    how_many = f"-c{count}" if count is not None else f"-r{redundancy}"
    run(["par2", "create", "-q", f"-s{size}", how_many, "-n1", str(payload_path)])
    return split_set(path.read_bytes()
                     for path in sorted(payload_path.parent.glob(f"{payload_path.name}*.par2")))


def text_candidate(paths: Sequence[Path], archive: bytes) -> bytes:
    """The bytes to consider printing as text: one source's own content.

    A tar of several files is not something worth reading off a page, so only a
    lone file offers its content up; anything else falls back to the archive,
    which printable_text() will reject.
    """
    return paths[0].read_bytes() if len(paths) == 1 else archive


# -- the restore note, printed on every sheet -------------------------------

NOTE_TEMPLATE = """\
Scan every code on every sheet, any order, skipping unreadable ones:  \
zbarimg -q --raw -Sdisable -Sqrcode.enable sheet*.png > scan.txt
Lines read "{magic} {backup_id} <letter><n>/<total> <{encoding}>": group by letter, sort by n, \
decode each payload as {encoding}{padding}, and join into
  {data} -> {name}  (a missing n = {slice} zero bytes; truncate to {length})   \
{index} -> {name}.par2  (one complete copy)   {recovery} -> {name}.vol.par2  (any order)
Then  par2 repair {name}.par2  rebuilds up to {recovery_count} lost {codes}, and  {unpack}"""


# The note is the same shape whatever it says, and the sheet geometry depends
# on how tall it is, so the count is known before there is a backup to describe.
NOTE_LINES = len(NOTE_TEMPLATE.splitlines())


def restore_note(backup: Backup) -> list[str]:
    """How to get the secret back. Short, because it goes on every sheet.

    Written for a person holding nothing but the paper, so it never mentions
    this program: as far as the sheet is concerned, no such thing exists. Nor is
    it a runnable script -- a reader who knows a shell can write those lines
    themselves. What they cannot guess, and what this therefore spells out, is
    that the data codes are positional (a missing one has to be replaced by its
    own length in zero bytes, or every byte after it lands in the wrong slice)
    while the recovery codes are not, and that the three letters go into three
    separate files.

    It sits in the footer of every sheet rather than on a sheet of its own, so
    that no single sheet is the one that explains all the others.
    """
    unpack = (f"zstd -dc {backup.payload_name} | gpg -d | tar -xf -"
              if backup.encrypted else f"tar --zstd -xf {backup.payload_name}")
    padding = (' (pad with "=" to a multiple of 8)'
               if backup.encoding.name == "base32" else "")
    return NOTE_TEMPLATE.format(
        gpg=", gpg" if backup.encrypted else "",
        magic=MAGIC, backup_id=backup.backup_id, encoding=backup.encoding.name,
        padding=padding, name=backup.payload_name, slice=backup.slice_size,
        length=backup.payload_length, recovery_count=len(backup.recovery),
        codes="code" if len(backup.recovery) == 1 else "codes",
        unpack=unpack, data=STREAM_DATA, index=STREAM_INDEX,
        recovery=STREAM_RECOVERY).splitlines()


# -- the single-code case ---------------------------------------------------


@dataclass(frozen=True)
class SingleBackup:
    """A secret small enough that the machinery is only in the way."""

    backup_id: str
    title: str
    created: str
    source: Source
    payload: str
    literal: bool
    trailing_newline: bool
    text_body: str | None


def try_single(paths: Sequence[Path], *, encoding: Encoding, qr_version: int,
               title: str | None) -> SingleBackup | None:
    """A one-code backup, if the secret is short enough and needs no encryption.

    Worth the special case: a FileVault recovery key is 28 characters, and the
    most restorable thing that can be done with it is to put those characters
    in a QR code any phone can read, with no format, no tooling and no index.

    That only holds for a secret on one line. Anything with a line break in it
    goes in encoded instead, so that the bytes come back exactly as they went
    in -- the sha256 printed on the sheet has to mean something, and a scanner
    is free to mangle the whitespace around a multi-line payload.
    """
    if len(paths) != 1:
        return None
    raw = paths[0].read_bytes()
    text = printable_text(raw)
    literal = text is not None and "\n" not in text.strip()
    backup_id = new_backup_id()
    if literal:
        payload = text.strip()
    else:
        # The same tar the long path builds, so the file comes back under its
        # own name with the same two commands, rather than as a nameless blob.
        archive = run(["zstd", "-19", "-q", "-c"], stdin=tar_sources(paths))
        payload = Chunk(STREAM_SINGLE, 0, 1, archive).line(
            backup_id, encoding, MAX_INDEX_DIGITS)
    version = _qr_version(payload)
    if version is None or version > qr_version:
        return None
    source = describe_sources(paths)[0]
    return SingleBackup(
        backup_id=backup_id, title=title or source.name,
        created=datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z"),
        source=source, payload=payload, literal=literal,
        trailing_newline=literal and raw.endswith(b"\n"), text_body=text)


SINGLE_RECIPE_LITERAL = """\
This secret is one line, so the code holds it verbatim: no encoding, no
container, no index. Scan either code with anything -- a phone will do -- and
what comes out is the line itself.

Both codes on this sheet are identical; the second is there in case the first
is damaged. The line is printed above as well, so it can simply be typed.
{newline}"""

SINGLE_NEWLINE_NOTE = """
The original file ended in a newline, which is not in the code. Add one back
to match the sha256 above.
"""

SINGLE_RECIPE_BINARY = """\
This secret fits in one QR code, which holds a single line:

    {magic} {backup_id} {stream}{number} <{encoding}>

Scan either code -- they are identical, the second is a spare -- take the field
after the last space, decode it as {encoding}{padding} into payload.tar.zst, and
unpack that with:  tar --zstd -xf payload.tar.zst
"""


def single_recipe(backup: SingleBackup, encoding: Encoding) -> str:
    """How to read the sheet back, in prose. There is not enough of it to script."""
    if backup.literal:
        return SINGLE_RECIPE_LITERAL.format(
            newline=SINGLE_NEWLINE_NOTE if backup.trailing_newline else "")
    return SINGLE_RECIPE_BINARY.format(
        magic=MAGIC, backup_id=backup.backup_id, stream=STREAM_SINGLE,
        number=f"{1:0{MAX_INDEX_DIGITS}d}/{1:0{MAX_INDEX_DIGITS}d}",
        encoding=encoding.name,
        padding=' (pad with "=" to a multiple of 8)'
                if encoding.name == "base32" else "")


# -- laying it out on paper -------------------------------------------------

MM = 72 / 25.4
PAGE_SIZE = (210 * MM, 297 * MM)          # A4
# Wide enough for any printer's unprintable edge, narrow enough that the codes
# are not paying for margin they do not need.
MARGIN = 12 * MM
CONTENT_WIDTH = PAGE_SIZE[0] - 2 * MARGIN
CONTENT_HEIGHT = PAGE_SIZE[1] - 2 * MARGIN

# The footer carries the restore note as well as the identifying line, so how
# tall it is depends on the note. NOTE_SIZE is small but still readable; going
# smaller to win another row of codes would be a poor trade for the one piece
# of text that has to be legible in twenty years.
NOTE_SIZE, IDENTITY_SIZE = 6.2, 7.0

FONT_BODY, FONT_BOLD, FONT_MONO = "helv", "hebo", "cour"

# The base-14 fonts cover Latin-1 and nothing else, so a Japanese file name or
# title comes out as a row of dots. This face has no bold, so a Japanese heading
# is set in the regular weight rather than not at all.
FONT_CJK = "japan"

MONO_MIN_SIZE, MONO_MAX_SIZE = 4.5, 8.0
MONO_LEADING = 1.25

# The gap above the first row of codes. A code sheet has no heading of its own:
# every code is labelled underneath, and the footer says which sheet this is, so
# a title line would only cost a millimetre of every code on the page.
GRID_TOP_RESERVE = 6 * MM

# How small a printed module can get and still be read back. Measured, not
# guessed: sheets rendered as if printed and then degraded to a 150 dpi skewed
# photograph decode completely at 0.55 mm and fail almost entirely at 0.52 mm,
# which is the point where a module stops covering three camera pixels. The
# default sits one step above that cliff.
MIN_MODULE_MM = 0.58


def footer_height(note_lines: int = 0) -> float:
    """How much of the sheet the note and the identity line take off the bottom."""
    return (note_lines * NOTE_SIZE * MONO_LEADING
            + IDENTITY_SIZE * MONO_LEADING + 4 * MM)


def pick_font(text: str, wanted: str) -> str:
    """`wanted`, unless the text has characters only the CJK face can draw."""
    try:
        text.encode("latin-1")
    except UnicodeEncodeError:
        return FONT_CJK
    return wanted


def text_runs(text: str, wanted: str) -> list[tuple[str, str]]:
    """Split into (piece, font) runs, one per script.

    The CJK face can draw ASCII, but at full width, so a title like
    "PGP 秘密鍵" comes out spaced like a ransom note. Giving each script its own
    face costs a couple of extra runs and looks like writing.
    """
    runs: list[tuple[str, str]] = []
    for character in text:
        font = pick_font(character, wanted)
        if runs and runs[-1][1] == font:
            runs[-1] = (runs[-1][0] + character, font)
        else:
            runs.append((character, font))
    return runs


def text_width(text: str, font: str, size: float) -> float:
    """How wide the text will actually print. Measured, not counted.

    Counting characters would be wrong twice over: a Japanese character is twice
    the width of a Latin one, and Helvetica is proportional anyway.
    """
    return sum(pymupdf.get_text_length(piece, fontname=piece_font, fontsize=size)
               for piece, piece_font in text_runs(text, font))


def draw_runs(page: pymupdf.Page, left: float, baseline: float, text: str,
              font: str, size: float, color: tuple[float, float, float] | None = None) -> None:
    """Draw text, changing face where the script changes."""
    for piece, piece_font in text_runs(text, font):
        page.insert_text((left, baseline), piece, fontsize=size,
                         fontname=piece_font, color=color)
        left += pymupdf.get_text_length(piece, fontname=piece_font, fontsize=size)


def fitted_size(text: str, font: str, size: float, width: float,
                floor: float = 6.0) -> float:
    """`size`, shrunk just enough that `text` fits `width`."""
    length = text_width(text, font, size)
    return size if length <= width else max(floor, size * width / length)


@lru_cache(maxsize=None)
def qr_matrix(text: str) -> tuple[tuple[bool, ...], ...]:
    """The code as rows of modules, quiet zone included."""
    code = qrcode.QRCode(error_correction=QR_ERROR_CORRECTION, border=QR_BORDER)
    code.add_data(text)
    code.make(fit=True)
    return tuple(tuple(row) for row in code.get_matrix())


def draw_qr(page: pymupdf.Page, rect: pymupdf.Rect, text: str) -> int:
    """Draw the code into `rect` as vector paths. Returns its width in modules.

    Runs of dark modules along a row become one rectangle each, which cuts the
    path data roughly in half. They all go into a single shape so that the fill
    is one region: separate overlapping fills can show hairline seams where the
    renderer antialiases each edge in turn.
    """
    grid = qr_matrix(text)
    modules = len(grid)
    step = rect.width / modules
    shape = page.new_shape()
    for row_number, row in enumerate(grid):
        column = 0
        while column < modules:
            if not row[column]:
                column += 1
                continue
            start = column
            while column < modules and row[column]:
                column += 1
            shape.draw_rect(pymupdf.Rect(rect.x0 + start * step,
                                         rect.y0 + row_number * step,
                                         rect.x0 + column * step,
                                         rect.y0 + (row_number + 1) * step))
    shape.finish(fill=(0, 0, 0), color=None, width=0)
    shape.commit()
    return modules


def mono_size_for(lines: Sequence[str], width: float) -> float:
    """The largest readable monospace size at which the widest line still fits."""
    widest = max((text_width(line, FONT_MONO, 1.0) for line in lines),
                 default=1.0) or 1.0
    return max(MONO_MIN_SIZE, min(MONO_MAX_SIZE, width / widest))


def longest_prefix(line: str, font: str, size: float, width: float) -> int:
    """How many characters of `line` fit in `width`. At least one, always."""
    low, high = 1, len(line)
    while low < high:
        middle = (low + high + 1) // 2
        if text_width(line[:middle], font, size) <= width:
            low = middle
        else:
            high = middle - 1
    return low


def wrap_mono(lines: Sequence[str], width: float, size: float) -> tuple[list[str], bool]:
    """Hard-wrap over-wide lines, and say whether anything had to be wrapped.

    Wrapping changes what a person retyping the page would get, so the caller
    has to be able to say so on the sheet rather than quietly corrupting it.
    """
    wrapped, folded = [], False
    for line in lines:
        if text_width(line, FONT_MONO, size) <= width:
            wrapped.append(line)
            continue
        folded = True
        rest = line
        while rest:
            cut = longest_prefix(rest, FONT_MONO, size, width)
            wrapped.append(rest[:cut])
            rest = rest[cut:]
    return wrapped, folded


class Sheet:
    """One PDF page, with a cursor that runs down it."""

    def __init__(self, document: pymupdf.Document, identity: str,
                 note: Sequence[str]):
        document.new_page(width=PAGE_SIZE[0], height=PAGE_SIZE[1])
        self._document = document
        self._number = document.page_count - 1
        self.y = MARGIN
        self._identity = identity
        self._note = note

    @property
    def page(self) -> pymupdf.Page:
        """Fetched afresh every time: adding a page invalidates the older objects."""
        return self._document[self._number]

    @property
    def remaining(self) -> float:
        return PAGE_SIZE[1] - MARGIN - footer_height(len(self._note)) - self.y

    def text(self, content: str, size: float = 9.0, font: str = FONT_BODY,
             gap: float = 0.0) -> None:
        self.y += size * MONO_LEADING + gap
        draw_runs(self.page, MARGIN, self.y, content, font,
                  fitted_size(content, font, size, CONTENT_WIDTH))

    def heading(self, content: str) -> None:
        self.text(content, size=13.0, font=FONT_BOLD, gap=4 * MM)
        self.y += 1.5 * MM

    def block(self, lines: Sequence[str], size: float, font: str = FONT_MONO,
              gap: float = 0.0) -> None:
        self.y += gap
        step = size * MONO_LEADING
        for line in lines:
            self.y += step
            if line:
                draw_runs(self.page, MARGIN, self.y, line, font, size)

    def rule(self) -> None:
        self.y += 2 * MM
        self.page.draw_line((MARGIN, self.y), (MARGIN + CONTENT_WIDTH, self.y),
                            color=(0.7, 0.7, 0.7), width=0.5)

    def qr_grid(self, labelled: Sequence[tuple[str, str]], columns: int,
                side: float, drawn: Callable[[], None] | None = None) -> None:
        """Draw codes in a grid, each with its header line underneath."""
        label_size = 6.5
        cell_width = CONTENT_WIDTH / columns
        rows_total = (len(labelled) + columns - 1) // columns
        for position, (payload, label) in enumerate(labelled):
            column, row = position % columns, position // columns
            # A last row with a gap in it looks like a code fell off the page,
            # so centre whatever is on it.
            in_row = columns if row < rows_total - 1 else len(labelled) - row * columns
            indent = (columns - in_row) * cell_width / 2
            left = MARGIN + indent + column * cell_width + (cell_width - side) / 2
            top = self.y + row * (side + 4 * MM + label_size)
            draw_qr(self.page, pymupdf.Rect(left, top, left + side, top + side),
                    payload)
            self.page.insert_text((left, top + side + label_size + 1),
                                  label, fontsize=label_size, fontname=FONT_MONO)
            if drawn is not None:
                drawn()
        rows = (len(labelled) + columns - 1) // columns
        self.y += rows * (side + 4 * MM + label_size)

    def finish(self, number: int, total: int) -> None:
        """Draw the footer: the restore note, then who this sheet belongs to."""
        top = PAGE_SIZE[1] - MARGIN - footer_height(len(self._note))
        self.page.draw_line((MARGIN, top), (MARGIN + CONTENT_WIDTH, top),
                            color=(0.7, 0.7, 0.7), width=0.5)
        baseline = top
        for line in self._note:
            baseline += NOTE_SIZE * MONO_LEADING
            draw_runs(self.page, MARGIN, baseline, line, FONT_MONO,
                      fitted_size(line, FONT_MONO, NOTE_SIZE, CONTENT_WIDTH, floor=4.0))
        line = f"{self._identity}   ·   sheet {number} of {total}"
        draw_runs(self.page, MARGIN, PAGE_SIZE[1] - MARGIN, line, FONT_BODY,
                  fitted_size(line, FONT_BODY, IDENTITY_SIZE, CONTENT_WIDTH, floor=4.5),
                  color=(0.35, 0.35, 0.35))


# -- showing that something is happening ------------------------------------


class Progress(LiveLine):
    """One line that says which stage this is and how far through the codes.

    Drawing a few hundred codes takes long enough to look like a hang, and the
    machinery in lib.progressbar is exactly for that: one line, rewritten, that
    gets out of the way of ordinary output and draws nothing at all when there
    is no terminal to draw on.
    """

    def __init__(self, enabled: bool) -> None:
        super().__init__(enabled=enabled)   # LiveLine goes to stderr by default
        self.stage = ""
        self.done = 0
        self.total = 0

    def parts(self) -> list[str | BarSlot]:
        if not self.total:
            return [self.stage]
        return [f"{self.stage:<16}", BarSlot(self.done / self.total),
                f"{self.done:>4}/{self.total}"]

    def begin(self, stage: str, total: int = 0) -> None:
        with self.lock:
            self.stage, self.total, self.done = stage, total, 0
            self.refresh()

    def step(self) -> None:
        with self.lock:
            self.done += 1
            self.refresh()


# -- assembling the document ------------------------------------------------

# Codes always sit two to a row: any narrower and the modules stop surviving a
# printer, and a single wide column wastes half the sheet.
QR_COLUMNS = 2

# The header line printed under each code.
QR_LABEL_SIZE = 6.5

# Copies of the par2 index to print. par2 cannot rebuild its own index, so the
# index is protected by repetition rather than by recovery codes -- but a copy
# on every sheet is a third of the ink for no more safety than a handful spread
# through the stack, so a long document gets five and a short one three.
INDEX_COPIES_SMALL, INDEX_COPIES_LARGE, SHORT_DOCUMENT = 3, 5, 10


def paginate[T](items: Sequence[T], per_page: int) -> list[list[T]]:
    return [list(items[start:start + per_page])
            for start in range(0, len(items), per_page)] or [[]]


def qr_side(per_page: int) -> float:
    """How big each code can be, given how many share a sheet."""
    rows = (per_page + QR_COLUMNS - 1) // QR_COLUMNS
    usable = CONTENT_HEIGHT - footer_height(NOTE_LINES) - GRID_TOP_RESERVE
    return min(CONTENT_WIDTH / QR_COLUMNS - 6 * MM,
               usable / rows - (4 * MM + QR_LABEL_SIZE))


# A backup small enough to fit on one sheet gets a heading of three lines
# instead of the metadata table: everything the table would have said is in the
# footer note and under the codes already, and the table costs a whole row of
# codes -- which, at this size, is the difference between one sheet and two.
COMPACT_HEADER = 18 * MM


def compact_side(codes: int) -> float:
    """How big each code can be if the whole backup shares one sheet."""
    rows = max(1, -(-codes // QR_COLUMNS))
    return min(CONTENT_WIDTH / QR_COLUMNS - 6 * MM,
               (CONTENT_HEIGHT - footer_height(NOTE_LINES) - COMPACT_HEADER) / rows
               - (4 * MM + QR_LABEL_SIZE))


def qr_version_for(side: float, min_module: float) -> int:
    """The densest QR version whose modules still print at least `min_module` mm.

    Version, not module size, is what the encoder takes, but module size is what
    decides whether a scanner can read the sheet -- and it depends on how many
    codes share the sheet. So the caller asks for millimetres and this works out
    the version, rather than the other way round.
    """
    modules = side / MM / min_module
    version = int((modules - 2 * QR_BORDER - 17) // 4)
    if version < 1:
        raise BackupError(
            f"a code {side / MM:.0f} mm across cannot hold {min_module} mm modules; "
            "lower --per-page or --min-module")
    return min(40, version)


def index_copies(sheets: int) -> int:
    """How many sheets should carry a copy of the index."""
    wanted = INDEX_COPIES_SMALL if sheets <= SHORT_DOCUMENT else INDEX_COPIES_LARGE
    return min(sheets, wanted)


def spread_index(body: Sequence[Chunk], index: Sequence[Chunk],
                 copies: int) -> list[list[Chunk]]:
    """Slot `copies` copies of the index evenly through the code sequence.

    Returns groups that must not be broken up: a copy of the index split over
    two sheets is a complete copy on neither, and it is the one thing par2
    cannot rebuild. Into the sequence rather than onto chosen sheet numbers,
    because how many sheets there will be is not known until the copies are in,
    and a sheet number picked before the fact can fall off the end and quietly
    lose a copy. The first copy goes in front of everything and the last behind
    it, because a stack loses its outside sheets first.
    """
    groups = [[chunk] for chunk in body]
    if not index or copies < 1:
        return groups
    points = ({0} if copies == 1
              else {round(step * len(body) / (copies - 1)) for step in range(copies)})
    out: list[list[Chunk]] = []
    for position in range(len(body) + 1):
        if position in points:
            out.append(list(index))
        if position < len(body):
            out.append(groups[position])
    return out


def fill_sheets(sections: Sequence[Sequence[Sequence[Chunk]]], per_page: int,
                cover_slots: int) -> list[list[Chunk]]:
    """Pack groups onto sheets, starting each section on a fresh one.

    A group never straddles a sheet. Only an index copy is ever longer than one
    code, and one longer than a whole sheet cannot be kept whole -- at which
    point it is let through split, because refusing to print anything would be
    worse than printing something imperfect.
    """
    sheets: list[list[Chunk]] = []
    page: list[Chunk] = []
    capacity = cover_slots
    for section in sections:
        if sheets or page:
            sheets.append(page)
            page, capacity = [], per_page
        for group in section:
            if page and len(page) + len(group) > capacity:
                sheets.append(page)
                page, capacity = [], per_page
            page += group
    sheets.append(page)
    return sheets


def plan_sheets(backup: Backup, per_page: int, cover_slots: int,
                separate: bool = False) -> list[list[Chunk]]:
    """Which codes go on which sheet, index copies included.

    The cover has whatever room the metadata left it, so it is planned as a
    sheet with its own capacity rather than as something separate.

    `separate` starts the recovery codes on a fresh sheet. Mixing the two puts
    part of a sheet's own cover on the sheet itself, so adding recovery codes
    stops buying a spare sheet as fast as it should -- which is what
    --whole-sheet is asking for. It makes no difference to what a loss costs:
    par2 needs only that the data codes lost are covered by the recovery codes
    that survive, so k sheets are restorable exactly when the codes on them,
    index copies aside, number no more than the whole recovery stream. That
    count does not depend on how the two streams are shuffled together, which
    is why they are not.

    How many index copies to print depends on how many sheets there are, which
    depends on the copies; going round a few times settles it, since copies
    only ever add sheets.
    """
    body = ([list(backup.data), list(backup.recovery)] if separate
            else [list(backup.data) + list(backup.recovery)])
    copies = INDEX_COPIES_SMALL
    sheets = fill_sheets([[[chunk] for chunk in part] for part in body],
                         per_page, cover_slots)
    for _ in range(4):
        share = -(-copies // len(body))
        sheets = fill_sheets([spread_index(part, backup.index, share) for part in body],
                             per_page, cover_slots)
        wanted = index_copies(len(sheets))
        if wanted == copies:
            break
        copies = wanted
    return sheets


def sheets_losable(pages: Sequence[Sequence[Chunk]], recovery_total: int) -> int:
    """How many whole sheets can go missing with the rest still restorable.

    A percentage of redundancy says nothing about sheets: a lost sheet takes all
    its data codes at once, and par2 can only rebuild as many as there are
    surviving recovery codes. A sheet holding the last index copy takes
    everything with it. Checked exhaustively as far as the cover claims.
    """
    def survivable(lost: frozenset[int]) -> bool:
        gone = [chunk for number in lost for chunk in pages[number]]
        lost_data = sum(1 for chunk in gone if chunk.stream == STREAM_DATA)
        lost_recovery = sum(1 for chunk in gone if chunk.stream == STREAM_RECOVERY)
        index_left = any(any(chunk.stream == STREAM_INDEX for chunk in page)
                         for number, page in enumerate(pages) if number not in lost)
        return index_left and lost_data <= recovery_total - lost_recovery

    for count in (1, 2, 3):
        if count >= len(pages) or not all(
                survivable(frozenset(lost))
                for lost in combinations(range(len(pages)), count)):
            return count - 1
    return 3


def recovery_shortfall(pages: Sequence[Sequence[Chunk]], recovery_total: int) -> int:
    """How many more recovery codes it would take to make any one sheet spare.

    Counting alone will not do it: a sheet holding data and recovery codes
    together takes some of its own cover with it, so the answer depends on how
    the codes actually fell across the sheets.
    """
    worst = 0
    for page in pages:
        lost_data = sum(1 for chunk in page if chunk.stream == STREAM_DATA)
        lost_recovery = sum(1 for chunk in page if chunk.stream == STREAM_RECOVERY)
        worst = max(worst, lost_data - (recovery_total - lost_recovery))
    return max(0, worst)


def loss_sentence(losable: int) -> str:
    if losable == 0:
        return "none - every sheet is needed; keep them together"
    if losable >= 3:
        return "any 3 sheets, and probably more"
    return f"any {losable} sheet{'s' if losable > 1 else ''}"


def fit_text(lines: Sequence[str], width: float,
             height: float) -> tuple[float, list[str], bool] | None:
    """The largest size at which the text fits the space, or None if it cannot."""
    for size in (MONO_MAX_SIZE, 7.0, 6.0, 5.0, MONO_MIN_SIZE):
        wrapped, folded = wrap_mono(lines, width, size)
        if len(wrapped) * size * MONO_LEADING <= height:
            return size, wrapped, folded
    return None


def metadata_rows(backup: Backup) -> list[tuple[str, str]]:
    rows = [
        ("Backup id", backup.backup_id),
        ("Created", backup.created),
        ("Encryption", "gpg --symmetric --armor (passphrase needed to restore)"
                       if backup.encrypted else "none - these sheets are the secret"),
        ("Payload", f"{backup.payload_name}, {backup.payload_length:,} bytes"),
        ("Chunking", f"{backup.slice_size} bytes per data chunk, {backup.encoding.name}, "
                     f"QR error correction M"),
        ("QR codes", ""),          # both of these wait for the finished layout
        ("Redundancy", f"{backup.redundancy}% - any {len(backup.recovery)} "
                       f"of the data codes can be lost and rebuilt"),
        ("Sheet loss", ""),
    ]
    for number, source in enumerate(backup.sources):
        rows.append(("Source" if number == 0 else "", f"{source.name}, {source.size:,} bytes"))
        rows.append(("", f"sha256 {source.digest}"))
    return rows


METADATA_SIZE = 8.0
METADATA_INDENT = 26 * MM


def draw_metadata(sheet: Sheet, rows: Sequence[tuple[str, str]]) -> dict[str, float]:
    """Draw the label/value table. Rows left empty come back as baselines.

    One of them cannot be written yet: how many sheets can be lost depends on
    how the codes end up laid out, which depends in turn on how much room this
    table leaves. Reserving the line keeps the arithmetic in one direction.
    """
    placeholders: dict[str, float] = {}
    for label, value in rows:
        sheet.y += METADATA_SIZE * MONO_LEADING
        if label:
            sheet.page.insert_text((MARGIN, sheet.y), label, fontsize=METADATA_SIZE,
                                   fontname=FONT_BOLD)
        if value:
            draw_metadata_value(sheet.page, sheet.y, value)
        else:
            placeholders[label] = sheet.y
    return placeholders


def draw_metadata_value(page: pymupdf.Page, baseline: float, value: str) -> None:
    width = CONTENT_WIDTH - METADATA_INDENT
    draw_runs(page, MARGIN + METADATA_INDENT, baseline, value, FONT_MONO,
              fitted_size(value, FONT_MONO, METADATA_SIZE, width, floor=5.0))


def chunk_labels(backup: Backup, chunks: Sequence[Chunk]) -> list[tuple[str, str]]:
    """Each chunk as (QR payload, the header line printed under it)."""
    pairs = []
    for chunk in chunks:
        line = chunk.line(backup.backup_id, backup.encoding, backup.digits)
        pairs.append((line, line.rsplit(" ", 1)[0]))
    return pairs


def module_pitch(labelled: Sequence[tuple[str, str]], side: float) -> float:
    """The printed size of one QR module, in millimetres, for the densest code."""
    worst = max((len(qr_matrix(payload)) for payload, _ in labelled), default=1)
    return side / MM / worst


def version_span(labelled: Sequence[tuple[str, str]]) -> tuple[int, int]:
    """The lowest and highest QR version in use.

    Worth saying out loud, because the three streams are sized independently
    and a wide span means the sheet mixes dense codes with sparse ones: the
    dense ones are then the only ones that matter, and the paper spent on the
    sparse ones is paper that could have been carrying more.
    """
    sizes = [len(qr_matrix(payload)) for payload, _ in labelled] or [21]

    def version(modules: int) -> int:
        return (modules - 2 * QR_BORDER - 17) // 4

    return version(min(sizes)), version(max(sizes))


def sheet_identity(backup: Backup) -> str:
    """The line along the very bottom of every sheet.

    The digest is on it so that a sheet separated from the cover still says
    what the restored file has to hash to; sixteen hex digits is far more than
    enough to catch a bad restore and short enough to stay on the line. Several
    sources have several digests, which will not fit, so those stay on the
    cover where there is room for all of them.
    """
    parts = [f"{MAGIC} {backup.backup_id}", backup.title, backup.created]
    if len(backup.sources) == 1:
        parts.append(f"sha256 {backup.sources[0].digest[:16]}")
    return "   ·   ".join(parts)


@dataclass(frozen=True)
class Rendered:
    """What the finished document turned out to be."""

    sheets: int
    pitch: float
    losable: int
    shortfall: int
    versions: tuple[int, int]


def render_backup(backup: Backup, out_path: Path, *, per_page: int,
                  min_module: float, text_pages_allowed: bool,
                  separate_streams: bool = False,
                  progress: Progress | None = None) -> Rendered:
    """Write the PDF and report what came out of it."""
    note = restore_note(backup)
    side = qr_side(per_page)
    row_height = side + 4 * MM + QR_LABEL_SIZE
    identity = sheet_identity(backup)

    document = pymupdf.open()
    sheets: list[Sheet] = []
    drawn: list[tuple[str, str]] = []
    step = progress.step if progress is not None else None

    def code_sheet(chunks: Sequence[Chunk]) -> None:
        sheet = Sheet(document, identity, note)
        sheets.append(sheet)
        sheet.y += GRID_TOP_RESERVE
        labels = chunk_labels(backup, chunks)
        sheet.qr_grid(labels, QR_COLUMNS, side, step)
        drawn.extend(labels)

    cover = Sheet(document, identity, note)
    sheets.append(cover)
    cover.heading(backup.title)
    cover.y += 2 * MM
    placeholders = draw_metadata(cover, metadata_rows(backup))
    cover.rule()

    # The content goes on the cover if it fits there, and nowhere otherwise:
    # half a key is no use to anyone typing it back in, and a spilled one costs
    # a sheet per page. Asking for --text says the sheets are worth spending.
    body = backup.text_body.splitlines() if backup.text_body is not None else []
    spilled: list[list[str]] = []
    text_size, text_folded = MONO_MAX_SIZE, False
    if body:
        fitted = fit_text(body, CONTENT_WIDTH, cover.remaining - 14 * MM)
        if fitted is not None:
            text_size, lines, text_folded = fitted
            cover.text(backup.text_label, size=9.0, font=FONT_BOLD, gap=1 * MM)
            cover.block(lines, text_size, gap=1 * MM)
        elif text_pages_allowed:
            text_size = mono_size_for(body, CONTENT_WIDTH)
            lines, text_folded = wrap_mono(body, CONTENT_WIDTH, text_size)
            per_sheet = max(1, int((CONTENT_HEIGHT - footer_height(NOTE_LINES)
                                    - GRID_TOP_RESERVE)
                                   / (text_size * MONO_LEADING)))
            spilled = paginate(lines, per_sheet)

    cover_slots = max(0, int(cover.remaining / row_height)) * QR_COLUMNS
    pages = plan_sheets(backup, per_page, cover_slots, separate_streams)
    if progress is not None:
        progress.begin("drawing codes", sum(len(page) for page in pages))
    losable = sheets_losable(pages, len(backup.recovery))
    carrying = sum(1 for page in pages
                   if any(chunk.stream == STREAM_INDEX for chunk in page))
    draw_metadata_value(
        cover.page, placeholders["QR codes"],
        f"{len(backup.data)} data + {len(backup.recovery)} recovery + "
        f"{len(backup.index)} index, a copy of the index on {carrying} of "
        f"{len(pages)} sheets")
    draw_metadata_value(cover.page, placeholders["Sheet loss"], loss_sentence(losable))
    if pages[0]:
        cover.y += 3 * MM
        labels = chunk_labels(backup, pages[0])
        cover.qr_grid(labels, QR_COLUMNS, side, step)
        drawn.extend(labels)

    for number, page in enumerate(spilled, start=1):
        sheet = Sheet(document, identity, note)
        sheets.append(sheet)
        sheet.heading(f"{backup.text_label} ({number}/{len(spilled)})")
        if text_folded:
            sheet.text("Long lines are wrapped to fit; the codes are authoritative.",
                       size=7.5)
        if backup.encrypted:
            sheet.text("Ciphertext. Safe to read, and can be typed back in if every "
                       "code is lost.", size=7.5)
        sheet.block(page, text_size, gap=2 * MM)

    for page in pages[1:]:
        code_sheet(page)

    if progress is not None:
        progress.begin("writing the PDF")
    for number, sheet in enumerate(sheets, start=1):
        sheet.finish(number, len(sheets))
    document.save(out_path, garbage=3, deflate=True)
    document.close()
    return Rendered(len(sheets), module_pitch(drawn, side), losable,
                    recovery_shortfall(pages, len(backup.recovery)),
                    version_span(drawn))


def render_compact(backup: Backup, out_path: Path, min_module: float,
                   progress: Progress | None = None) -> Rendered:
    """One sheet holding the lot: a three-line heading, every code, the note."""
    note = restore_note(backup)
    codes = list(backup.index) + list(backup.data) + list(backup.recovery)
    side = compact_side(len(codes))
    identity = f"{MAGIC} {backup.backup_id}   ·   {backup.title}   ·   {backup.created}"

    document = pymupdf.open()
    sheet = Sheet(document, identity, note)
    sheet.text(backup.title, size=11.0, font=FONT_BOLD, gap=1 * MM)
    source = backup.sources[0]
    sheet.text(("encrypted with gpg --symmetric --armor" if backup.encrypted
                else "not encrypted - this sheet is the secret")
               + f"   ·   {source.name}, {source.size:,} bytes", size=7.5)
    sheet.text(f"sha256 {source.digest}", size=7.5, font=FONT_MONO)
    sheet.y += 3 * MM
    labels = chunk_labels(backup, codes)
    if progress is not None:
        progress.begin("drawing codes", len(labels))
    sheet.qr_grid(labels, QR_COLUMNS, side,
                  progress.step if progress is not None else None)
    sheet.finish(1, 1)
    document.save(out_path, garbage=3, deflate=True)
    document.close()
    return Rendered(1, module_pitch(labels, side), 0, 0, version_span(labels))


def render_single(backup: SingleBackup, encoding: Encoding,
                  out_path: Path) -> Rendered:
    """One sheet: the secret twice over, and how to read it back."""
    identity = f"{MAGIC} {backup.backup_id}   ·   {backup.title}   ·   {backup.created}"
    note = single_recipe(backup, encoding).splitlines()
    document = pymupdf.open()
    sheet = Sheet(document, identity, note)
    sheet.heading(backup.title)
    sheet.text("Paper backup, small enough for a single QR code.", size=9.0)
    sheet.y += 2 * MM
    draw_metadata(sheet, [
        ("Backup id", backup.backup_id),
        ("Created", backup.created),
        ("Encryption", "none - this sheet is the secret"),
        ("Contents", "the line itself, verbatim in the code"
                     if backup.literal else
                     f"the file, tar + zstd + {encoding.name}, in the code"),
        ("Source", f"{backup.source.name}, {backup.source.size:,} bytes"),
        ("", f"sha256 {backup.source.digest}"),
    ])
    if backup.text_body is not None:
        sheet.rule()
        lines = backup.text_body.strip().splitlines()
        size = mono_size_for(lines, CONTENT_WIDTH)
        wrapped, _ = wrap_mono(lines, CONTENT_WIDTH, size)
        sheet.text("Content", size=9.0, font=FONT_BOLD, gap=2 * MM)
        sheet.block(wrapped, size, gap=1 * MM)
    sheet.rule()
    side = min(78 * MM, (sheet.remaining - 10 * MM) )
    sheet.y += 2 * MM
    sheet.qr_grid([(backup.payload, "copy 1"), (backup.payload, "copy 2")],
                  QR_COLUMNS, side)
    sheet.finish(1, 1)
    document.save(out_path, garbage=3, deflate=True)
    document.close()
    labelled = [(backup.payload, "")]
    return Rendered(1, module_pitch(labelled, side), 0, 0, version_span(labelled))


# -- reading the sheets back ------------------------------------------------


def images_from(path: Path, dpi: int):
    """Every page of a PDF, or the image file itself, as PIL images."""
    from PIL import Image
    if path.suffix.lower() == ".pdf":
        with pymupdf.open(path) as document:
            for page in document:
                pixmap = page.get_pixmap(dpi=dpi)
                yield Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        return
    with Image.open(path) as image:
        yield image.convert("RGB")


def sheet_count(paths: Sequence[Path]) -> int:
    """How many pages there are to look at, for the progress line."""
    total = 0
    for path in paths:
        if path.suffix.lower() == ".pdf":
            with pymupdf.open(path) as document:
                total += document.page_count
        else:
            total += 1
    return total


def scan_payloads(paths: Sequence[Path], dpi: int,
                  progress: Progress | None = None) -> list[str]:
    """Every QR code found in the given PDFs and images.

    Rasterising a sheet and hunting it for codes is the slow half of a restore,
    so the count is of sheets rather than files: a one-file PDF would otherwise
    sit there saying nothing at all.
    """
    from pyzbar import pyzbar
    from pyzbar.pyzbar import ZBarSymbol
    if progress is not None:
        progress.begin("scanning sheets", sheet_count(paths))
    found: list[str] = []
    for path in paths:
        before = len(found)
        for image in images_from(path, dpi):
            for symbol in pyzbar.decode(image, symbols=[ZBarSymbol.QRCODE]):
                found.append(symbol.data.decode("utf-8", errors="replace"))
            if progress is not None:
                progress.step()
        line = f"  {path.name}: {len(found) - before} code(s)"
        if progress is not None:
            progress.report(line)
        else:
            print(line, file=sys.stderr)
    return found


def gpg_decrypt(armor: bytes, passphrase: str) -> bytes:
    read_fd, write_fd = os.pipe()
    try:
        os.write(write_fd, passphrase.encode("utf-8"))
    finally:
        os.close(write_fd)
    try:
        return run(["gpg", "--batch", "--quiet", "--decrypt", "--pinentry-mode", "loopback",
                    "--passphrase-fd", str(read_fd)], stdin=armor, extra_fds=(read_fd,))
    finally:
        os.close(read_fd)


def collect(chunks: Sequence[ParsedChunk], stream: str) -> tuple[dict[int, bytes], int]:
    """The chunks of one stream by number, and how many there should be."""
    wanted = {chunk.index: chunk.raw for chunk in chunks if chunk.stream == stream}
    totals = {chunk.total for chunk in chunks if chunk.stream == stream}
    return wanted, max(totals) if totals else 0


def restore(payloads: Sequence[str], *, encoding: Encoding, directory: Path,
            workdir: Path, backup_id: str | None) -> list[str]:
    """Turn scanned QR payloads back into files. Returns what was written."""
    literals = [text for text in payloads if not text.startswith(f"{MAGIC} ")]
    parsed = [chunk for chunk in (parse_chunk(text, encoding) for text in payloads)
              if chunk is not None]
    if not parsed:
        if not literals:
            raise BackupError("no QR codes found - try a higher --dpi, or a better scan")
        return write_literals(literals, directory)

    found_ids = sorted({chunk.backup_id for chunk in parsed})
    if backup_id is None and len(found_ids) > 1:
        raise BackupError("sheets from several backups here (" + ", ".join(found_ids) +
                          ") - pick one with --id")
    chosen = backup_id or found_ids[0]
    chunks = [chunk for chunk in parsed if chunk.backup_id == chosen]
    if not chunks:
        raise BackupError(f"no codes for backup {chosen}; found " + ", ".join(found_ids))

    singles, _ = collect(chunks, STREAM_SINGLE)
    if singles:
        payload_path = workdir / "payload.tar.zst"
        payload_path.write_bytes(singles[0])
        return unpack(payload_path, directory)

    index_parts, index_total = collect(chunks, STREAM_INDEX)
    missing_index = [number for number in range(index_total) if number not in index_parts]
    if missing_index:
        raise BackupError(
            f"the PAR2 index is incomplete: missing {missing_index} of {index_total}. "
            "Every survival kit sheet carries a full copy; scan another one.")
    index_blob = b"".join(index_parts[number] for number in range(index_total))

    name = par2_payload_name(index_blob)
    size, length = slice_size(index_blob), file_length(index_blob)
    data_parts, data_total = collect(chunks, STREAM_DATA)
    expected = -(-length // size)
    data_total = max(data_total, expected)
    lost = [number for number in range(data_total) if number not in data_parts]
    recovery_parts, recovery_total = collect(chunks, STREAM_RECOVERY)

    print(f"  backup {chosen}: {len(data_parts)}/{data_total} data, "
          f"{len(recovery_parts)}/{recovery_total} recovery, index complete",
          file=sys.stderr)
    if lost:
        print(f"  {len(lost)} data code(s) missing: {lost}", file=sys.stderr)
        if len(lost) > len(recovery_parts):
            raise BackupError(
                f"{len(lost)} codes are missing but only {len(recovery_parts)} recovery "
                "codes were found - scan more sheets")

    payload = bytearray()
    for number in range(data_total):
        payload += data_parts.get(number, bytes(size))
    payload_path = workdir / name
    payload_path.write_bytes(bytes(payload[:length]))
    (workdir / f"{name}.par2").write_bytes(index_blob)
    (workdir / f"{name}.vol.par2").write_bytes(
        b"".join(recovery_parts[number] for number in sorted(recovery_parts)))

    run(["par2", "repair", "-q", str(workdir / f"{name}.par2")])
    return unpack(payload_path, directory)


def par2_payload_name(index_blob: bytes) -> str:
    """The payload's own file name, which par2 recorded when it protected it."""
    name = Path(file_name(index_blob)).name
    if not name:
        raise BackupError("the PAR2 index does not name the payload file")
    return name


def unpack(payload_path: Path, directory: Path) -> list[str]:
    """Undo the compress/encrypt pipeline, reading the shape off the file name."""
    directory.mkdir(parents=True, exist_ok=True)
    before = set(directory.iterdir())
    if payload_path.name.endswith(".asc.zst"):
        armor = run(["zstd", "-dc"], stdin=payload_path.read_bytes())
        archive = gpg_decrypt(armor, getpass.getpass("Passphrase: "))
        run(["tar", "-xf", "-", "-C", str(directory)], stdin=archive)
    else:
        run(["tar", "--zstd", "-xf", str(payload_path), "-C", str(directory)])
    return sorted(str(path) for path in set(directory.iterdir()) - before)


def write_literals(literals: Sequence[str], directory: Path) -> list[str]:
    """A single-code sheet holds the secret verbatim; show it rather than guess a name."""
    for text in dict.fromkeys(literals):
        print(text)
    return []


# -- command line -----------------------------------------------------------

# The conventional stand-in for stdin, kept in one place so the help text and
# the argument that triggers it cannot drift apart.
STDIN_ARGUMENT = "-"

DEFAULT_REDUNDANCY = 30
DEFAULT_PER_PAGE = 6

# How many times to raise the redundancy trying to free up a whole sheet before
# giving up and saying so. Each round adds recovery codes, which can add a sheet,
# which needs more recovery codes; it settles quickly or not at all.
WHOLE_SHEET_TRIES = 5
DEFAULT_DPI = 400

# Past this many sheets a paper backup stops being a sensible idea, so say so
# rather than quietly starting a print job that eats a ream.
SHEETS_WORTH_ASKING_ABOUT = 20


def ask_passphrase() -> str:
    while True:
        try:
            first = getpass.getpass("Passphrase: ")
            again = getpass.getpass("Passphrase (again): ") if first else ""
        except EOFError:
            # No terminal to ask on: getpass has fallen back to a stdin that
            # has nothing left in it, and looping would spin forever.
            raise BackupError("--encrypt needs a terminal to ask for the passphrase")
        if not first:
            print("  a passphrase is required for --encrypt", file=sys.stderr)
            continue
        if first == again:
            return first
        print("  they do not match", file=sys.stderr)


def run_wizard(opts: argparse.Namespace) -> None:
    """Fill in the options by asking, for the times this is run once a year."""
    if not interactive():
        raise BackupError("--wizard needs a terminal")
    while not opts.files:
        answer = prompt_text("File to back up")
        if not answer:
            raise BackupError("nothing to back up")
        if Path(answer).expanduser().is_file():
            opts.files = [answer]
        else:
            print("  no such file", file=sys.stderr)
    opts.encrypt = confirm("Encrypt with a passphrase (gpg --symmetric)?",
                           default=opts.encrypt)
    opts.redundancy = int(prompt_choice(
        "How much redundancy?",
        [("30", "30% - a third of the sheets can be lost (recommended)"),
         ("50", "50% - half of them"),
         ("100", "100% - every code printed twice over")],
        str(opts.redundancy), words=ENGLISH_CHOICE))
    opts.whole_sheet = confirm(
        "Add enough recovery codes that a whole lost sheet is survivable?",
        default=opts.whole_sheet)
    opts.text = prompt_choice(
        "Print the content as readable text as well?",
        [("fit", "only if it fits on the cover (recommended)"),
         ("full", "yes, on sheets of its own if it has to be"),
         ("never", "no, codes only")],
        opts.text, words=ENGLISH_CHOICE)
    opts.per_page = int(prompt_choice(
        "How many codes per sheet?",
        [("6", "6 - the densest that still scans from a photograph (recommended)"),
         ("4", "4 - bigger codes, about half again as many sheets"),
         ("2", "2 - one row, for a printer or scanner you do not trust")],
        str(opts.per_page), words=ENGLISH_CHOICE))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Back a secret up onto paper as QR codes, and read it back.",
        epilog="The sheets carry their own restore instructions, so this script "
               "is not needed to get the secret back.")
    parser.add_argument("files", nargs="*", metavar="FILE",
                        help="files to back up, or the PDF/images to restore from; "
                             f"{STDIN_ARGUMENT!r} reads stdin")
    parser.add_argument("--name", metavar="NAME",
                        help="the file name to keep what came in on stdin under, the "
                             "name it will be restored as (default: secret.txt, or "
                             "secret.bin if it is not text)")
    parser.add_argument("-o", "--output", type=Path, metavar="PATH",
                        help="where to write the PDF (default: <name>.paper.pdf)")
    parser.add_argument("-e", "--encrypt", action="store_true",
                        help="encrypt with gpg --symmetric before printing")
    parser.add_argument("-r", "--redundancy", type=int, default=DEFAULT_REDUNDANCY,
                        metavar="PERCENT",
                        help=f"par2 recovery, in percent (default: {DEFAULT_REDUNDANCY})")
    parser.add_argument("--encoding", choices=tuple(ENCODINGS), default="base32",
                        help="how chunk bytes become QR text (default: base32)")
    parser.add_argument("--min-module", type=float, default=MIN_MODULE_MM,
                        metavar="MM",
                        help="smallest printed module to allow, in mm; the densest "
                             f"code that respects it is used (default: {MIN_MODULE_MM})")
    parser.add_argument("--per-page", type=int, choices=(2, 4, 6), default=DEFAULT_PER_PAGE,
                        help=f"codes on a sheet (default: {DEFAULT_PER_PAGE})")
    parser.add_argument("--title", metavar="TEXT", help="heading for the sheets")
    parser.add_argument("--whole-sheet", action="store_true",
                        help="add enough recovery codes that any one whole sheet can "
                             "be lost, treating --redundancy as a floor")
    parser.add_argument("--text", choices=("fit", "full", "never"), default="fit",
                        help="print the content as text as well: on the cover if it "
                             "fits there, on sheets of its own, or not at all "
                             "(default: fit)")
    parser.add_argument("--wizard", action="store_true", help="ask instead of being told")
    parser.add_argument("-d", "--decode", action="store_true",
                        help="restore from a PDF or images of the sheets")
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI, metavar="N",
                        help=f"resolution to render a PDF at (default: {DEFAULT_DPI})")
    parser.add_argument("--id", metavar="ID",
                        help="which backup to restore, when sheets are mixed")
    parser.add_argument("-C", "--directory", type=Path, default=Path("."),
                        metavar="DIR", help="where to put restored files (default: .)")
    options = parser.parse_args()
    if not 0.2 <= options.min_module <= 5.0:
        parser.error("--min-module must be between 0.2 and 5.0 mm")
    if not 1 <= options.redundancy <= 1000:
        parser.error("--redundancy must be between 1 and 1000 percent")
    if options.decode and options.wizard:
        parser.error("--wizard and --decode do not go together")
    if options.files.count(STDIN_ARGUMENT) > 1:
        parser.error("stdin can only be read once")
    if options.name is not None and STDIN_ARGUMENT not in options.files:
        parser.error(f"--name says what to call stdin, so it needs {STDIN_ARGUMENT!r}")
    return options


def default_stdin_name(raw: bytes, decoding: bool) -> str:
    """A name for the stream, since the paper has to call it something."""
    if decoding:
        # images_from() tells a PDF from an image by its suffix; Pillow sniffs
        # the rest for itself, so one spare suffix covers every image format.
        return "sheets.pdf" if raw.startswith(b"%PDF-") else "sheets.img"
    return "secret.txt" if printable_text(raw) is not None else "secret.bin"


def stdin_file(workdir: Path, *, stored_name: str | None, decoding: bool) -> Path:
    """What arrived on stdin, written down so the rest of the run sees a file.

    Everything downstream works on named files -- tar, par2, the sha256 printed
    on the sheet -- and a restore has to put the secret back under some name, so
    the stream is given one here rather than being threaded through as bytes.
    """
    raw = sys.stdin.buffer.read()
    if not raw:
        raise BackupError("nothing arrived on stdin")
    name = stored_name or default_stdin_name(raw, decoding)
    if name in ("", ".", "..") or "/" in name:
        raise BackupError(f"--name must be a plain file name, not {name!r}")
    path = workdir / name
    path.write_bytes(raw)
    path.chmod(0o600)
    reattach_stdin_to_terminal()
    return path


def reattach_stdin_to_terminal() -> None:
    """Give the questions a terminal to read from, now that the pipe is spent.

    The passphrase and the "that is a lot of paper" confirmation both need an
    answer from a person, and stdin is where they go looking for one; with the
    secret itself having come in that way, there is nothing left there.
    """
    try:
        sys.stdin = open("/dev/tty", encoding="utf-8")
    except OSError:
        pass  # cron, a container, no controlling terminal: stay non-interactive


def existing_files(names: Sequence[str]) -> list[Path]:
    paths = [Path(name).expanduser() for name in names]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise BackupError("not a file: " + ", ".join(missing))
    return paths


def run_backup(opts: argparse.Namespace) -> int:
    require_commands("tar", "zstd", "par2", *(["gpg"] if opts.encrypt else []))
    progress = Progress(enabled=sys.stderr.isatty())
    paths = existing_files(opts.files)
    encoding = ENCODINGS[opts.encoding]
    out_path = opts.output or Path(f"{paths[0].name}.paper.pdf")

    version = qr_version_for(qr_side(opts.per_page), opts.min_module)
    # A backup that fits on one sheet is worth building for: it trades the
    # metadata table for a three-line heading, which leaves room for a third
    # row of codes but squeezes every code a little, so the density has to be
    # settled before par2 decides how many codes there will be.
    compact_version = qr_version_for(compact_side(opts.per_page), opts.min_module)
    if not opts.encrypt:
        single = try_single(paths, encoding=encoding, qr_version=version,
                            title=opts.title)
        if single is not None:
            report(out_path, render_single(single, encoding, out_path), None,
                   opts.min_module)
            return 0

    passphrase = ask_passphrase() if opts.encrypt else None
    with tempfile.TemporaryDirectory(prefix="paper_backup.") as name, progress:
        redundancy, count, asked = opts.redundancy, None, False
        # Whether a whole sheet is spare depends on how the codes fall across
        # the sheets, not just on how many there are, so the only honest way to
        # promise it is to lay the sheets out and look.
        for attempt in range(WHOLE_SHEET_TRIES):
            backup = build_backup(paths, encoding=encoding, redundancy=redundancy,
                                  qr_version=version, passphrase=passphrase,
                                  title=opts.title, workdir=Path(name),
                                  include_text=opts.text != "never",
                                  recovery_count=count, progress=progress)

            # A one-sheet layout squeezes the codes, so it needs its own build.
            # Only worth doing when the roomier build already fits in a sheet's
            # worth of codes, or the work is thrown away for nothing.
            if (attempt == 0 and not opts.whole_sheet and backup.text_body is None
                    and len(backup.data) + len(backup.recovery) + len(backup.index)
                    <= opts.per_page):
                compact = build_backup(
                    paths, encoding=encoding, redundancy=opts.redundancy,
                    qr_version=compact_version, passphrase=passphrase,
                    title=opts.title, workdir=Path(name),
                    include_text=False, progress=progress)
                if (len(compact.data) + len(compact.recovery) + len(compact.index)
                        <= opts.per_page):
                    result = render_compact(compact, out_path, opts.min_module,
                                            progress)
                    progress.close()
                    report(out_path, result, compact, opts.min_module)
                    return 0

            if not asked:
                rough = -(-backup.qr_count // opts.per_page)
                estimate = 1 + -(-(backup.qr_count + len(backup.index) * rough)
                                 // opts.per_page)
                if estimate > SHEETS_WORTH_ASKING_ABOUT and interactive():
                    progress.close()
                    print(f"  {backup.qr_count} codes, about {estimate} sheets "
                          f"({human(sum(s.size for s in backup.sources))} of input)",
                          file=sys.stderr)
                    if not confirm("That is a lot of paper. Go on?", default=False):
                        return 1
                asked = True
            result = render_backup(backup, out_path, per_page=opts.per_page,
                                   min_module=opts.min_module,
                                   text_pages_allowed=opts.text == "full",
                                   separate_streams=opts.whole_sheet,
                                   progress=progress)
            if not opts.whole_sheet or not result.shortfall:
                break
            count = len(backup.recovery) + result.shortfall
        progress.close()
        report(out_path, result, backup, opts.min_module)
    return 0


def report(out_path: Path, result: Rendered, backup: Backup | None,
           min_module: float) -> None:
    sheets, pitch, losable = result.sheets, result.pitch, result.losable
    print(f"{out_path}: {sheets} sheet(s)", file=sys.stderr)
    if backup is not None:
        print(f"  backup {backup.backup_id}, {backup.qr_count} codes, "
              f"survives losing {backup.lost_codes_survivable} of them",
              file=sys.stderr)
        # A percentage of redundancy is easy to misread as protection against
        # losing a sheet, which for a short backup it is not.
        if losable:
            print(f"  whole sheets that can go missing: {losable}", file=sys.stderr)
        elif sheets == 1:
            print(paint16("  one sheet, so there is nothing to spare: print it twice, "
                          "or use --whole-sheet", BRIGHT_YELLOW, sys.stderr),
                  file=sys.stderr)
        else:
            print(paint16("  no sheet is spare: losing any one of them loses the "
                          "backup (see --whole-sheet)", BRIGHT_YELLOW, sys.stderr),
                  file=sys.stderr)
    low, high = result.versions
    span = f"version {low}" if low == high else f"versions {low}-{high}"
    print(f"  smallest module: {pitch:.2f} mm (QR {span})", file=sys.stderr)
    if pitch < min_module:
        print(paint16(f"  warning: below {min_module} mm a printed code gets hard to "
                      "scan - try a smaller --per-page", BRIGHT_YELLOW, sys.stderr),
              file=sys.stderr)


def run_decode(opts: argparse.Namespace) -> int:
    require_commands("tar", "zstd", "par2")
    paths = existing_files(opts.files)
    progress = Progress(enabled=sys.stderr.isatty())
    # Scanning is the slow half; the rebuild after it talks for itself.
    with progress:
        payloads = scan_payloads(paths, opts.dpi, progress)
    with tempfile.TemporaryDirectory(prefix="paper_backup.") as name:
        written = restore(payloads, encoding=ENCODINGS[opts.encoding],
                          directory=opts.directory, workdir=Path(name),
                          backup_id=opts.id)
    for path in written:
        print(path)
    return 0


def main() -> int:
    opts = parse_args()
    try:
        if opts.wizard:
            run_wizard(opts)
        if not opts.files:
            print("Error: no files given (see --help)", file=sys.stderr)
            return 1
        with contextlib.ExitStack() as stack:
            if STDIN_ARGUMENT in opts.files:
                workdir = Path(stack.enter_context(
                    tempfile.TemporaryDirectory(prefix="paper_backup.stdin.")))
                given = stdin_file(workdir, stored_name=opts.name, decoding=opts.decode)
                opts.files = [str(given) if name == STDIN_ARGUMENT else name
                              for name in opts.files]
            return run_decode(opts) if opts.decode else run_backup(opts)
    except (BackupError, Par2Error) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        # A PDF that is not a PDF, an unreadable image, a full disk.
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
