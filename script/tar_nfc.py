#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
"""TARGET を tar（PAX 形式）にして標準出力へ流す。アーカイブ内の名前はすべて NFC に揃える。

tar-zstd-compress.sh --nfc の下請け（読み取り専用。TARGET には触らない）。

macOS では同じ名前が NFC でも NFD でも見える。SMB 共有（QNAP など）から読むと NFD で返り、
そのまま tar に入れると Linux / Windows で展開したときに濁点が分かれた名前になる。
ここでは名前だけを NFC にし、中身・パーミッション・更新日時はそのまま入れる。

usage: tar_nfc.py TARGET > out.tar
"""

import os
import sys
import tarfile
import unicodedata
from pathlib import Path


def nfc(name: str) -> str:
    return unicodedata.normalize("NFC", name)


def add_tree(archive: tarfile.TarFile, target: Path) -> int:
    """target 以下を名前順に入れ、入れた項目数を返す。シンボリックリンクはリンクのまま入れる。

    名前は tar -c と同じく、指定されたパスをそのまま（先頭の / だけ外して）使う。
    """
    count: int = 0
    seen: set[str] = set()

    def add(path: Path) -> None:
        nonlocal count
        arcname: str = nfc(str(path)).lstrip("/")
        if arcname in seen:
            raise SystemExit(f"tar_nfc.py: NFC にすると名前が重なる: {arcname}")
        seen.add(arcname)
        archive.add(path, arcname=arcname, recursive=False)
        count += 1

    add(target)
    if target.is_dir() and not target.is_symlink():
        for directory, subdirs, files in os.walk(target):
            subdirs.sort()
            for name in subdirs + sorted(files):
                add(Path(directory) / name)
    return count


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] in {"-h", "--help"}:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    target: Path = Path(sys.argv[1].rstrip("/") or "/")
    if not target.exists():
        raise SystemExit(f"tar_nfc.py: not found: {target}")
    with tarfile.open(fileobj=sys.stdout.buffer, mode="w|", format=tarfile.PAX_FORMAT) as archive:
        count: int = add_tree(archive, target)
    print(f"tar_nfc.py: {count} entries", file=sys.stderr)


if __name__ == "__main__":
    main()
