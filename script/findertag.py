#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///

"""
Finder Tag Editor

Add, remove, and list macOS Finder tags (`com.apple.metadata:_kMDItemUserTags`).

Usage:
    findertag.py FILE [FILE ...] add    TAG [TAG ...]
    findertag.py FILE [FILE ...] remove TAG [TAG ...]
    findertag.py FILE [FILE ...] list

    findertag.py ~/Documents/foo add MyTurn
    findertag.py ~/Documents/foo remove MyTurn
    findertag.py 案件*/ add MyTurn            # 複数パスまとめて

Notes:
    - The attribute holds a *plist array* of tag names. Writing a bare string
      with `xattr -w` does NOT register as a tag, and `xattr -d` drops every
      tag at once, so go through this script instead.
    - Tag *colors* are not per file: Finder colors a tag by what its own tag
      list says (Finder → 設定 → タグ). Entries written by Finder carry a
      "<name>\\n<color>" suffix, but Finder ignores it when displaying —
      verified 2026-09-07 by writing color 2 / 6 / none for one tag and seeing
      the same color on all three. So this script writes plain names and
      strips the suffix when comparing.
    - `mdls` / `mdfind` lag a few seconds behind; this script runs `mdimport`
      to nudge Spotlight, but the index may still be stale right afterwards.
      Use `list` to see the truth.
    - How the tags on this Mac are meant to be used is documented in
      ~/Documents/cowork/共通ルール.md ("Finderタグ" section).
"""

import argparse
import plistlib
import subprocess
import sys
from pathlib import Path

XATTR_KEY = "com.apple.metadata:_kMDItemUserTags"
ACTIONS = ("add", "remove", "list")


def load_plist(raw: bytes) -> list[str] | None:
    """Parse a tag plist; None when the value is not a readable plist array."""
    try:
        parsed = plistlib.loads(raw)
    except plistlib.InvalidFileException:
        # plistlib は旧形式(ASCII)の plist（`xattr -w '("Tag")'` で書ける形）を
        # 読めないので、plutil に変換させてから読む。
        converted = subprocess.run(
            ["plutil", "-convert", "xml1", "-o", "-", "-"],
            input=raw,
            capture_output=True,
        )
        if converted.returncode != 0:
            return None
        try:
            parsed = plistlib.loads(converted.stdout)
        except plistlib.InvalidFileException:
            return None
    return [str(tag) for tag in parsed] if isinstance(parsed, list) else None


def read_tags(path: Path) -> list[str] | None:
    """Return raw tag entries (one may carry a legacy "\\n<color>" suffix).

    None means the attribute holds something that must not be overwritten
    blindly (e.g. a bare string written by `xattr -w 'MyTurn'`).
    """
    # macOS の Python には os.getxattr が無い（Linux 専用）ため xattr コマンドを使う。
    result = subprocess.run(
        ["xattr", "-px", XATTR_KEY, str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []  # 属性が無い＝タグ無し
    return load_plist(bytes.fromhex(result.stdout.replace("\n", "").replace(" ", "")))


def write_tags(path: Path, tags: list[str]) -> None:
    """Replace all tags on `path`; an empty list removes the attribute."""
    if tags:
        payload = plistlib.dumps(tags, fmt=plistlib.FMT_BINARY).hex()
        subprocess.run(["xattr", "-wx", XATTR_KEY, payload, str(path)], check=True)
    else:
        subprocess.run(
            ["xattr", "-d", XATTR_KEY, str(path)],
            check=False,  # 元から無い場合もある
            stderr=subprocess.DEVNULL,
        )


def tag_name(entry: str) -> str:
    """Strip the legacy trailing color index from a raw tag entry."""
    return entry.split("\n")[0]


def apply_action(path: Path, action: str, tags: list[str]) -> bool:
    """Apply one action to one path. False when the path was left untouched."""
    current = read_tags(path)
    if current is None:
        # 上書きすると中身が分からないまま消えるので触らない
        print(
            f"findertag: {path}: 既存の値が plist 配列として読めないため触りません"
            f"（`xattr -px {XATTR_KEY}` で中身を確認してください）",
            file=sys.stderr,
        )
        return False
    if action == "list":
        for entry in current:
            print(f"{path}: {tag_name(entry)}")
        return True

    # 同名タグは色番号つきのものも含めて一旦落とす（add はこれで冪等になる）
    kept = [entry for entry in current if tag_name(entry) not in tags]
    if action == "add":
        kept.extend(tags)

    if kept != current:
        write_tags(path, kept)
    return True


def parse_args(argv: list[str]) -> tuple[list[Path], str, list[str]]:
    """Split `FILE... ACTION TAG...` into paths, action, and tag names."""
    parser = argparse.ArgumentParser(
        prog="findertag.py",
        description="Add, remove, and list macOS Finder tags.",
        epilog="example: findertag.py ~/Documents/foo add MyTurn",
    )
    parser.add_argument("args", nargs="*", metavar="FILE... ACTION [TAG...]")
    parsed = parser.parse_args(argv)

    positional: list[str] = parsed.args
    action_index = next(
        (i for i, value in enumerate(positional) if value in ACTIONS), None
    )
    if action_index is None or action_index == 0:
        parser.error(f"expected: FILE... ({'|'.join(ACTIONS)}) [TAG...]")

    action = positional[action_index]
    paths = [Path(value).expanduser() for value in positional[:action_index]]
    tags = positional[action_index + 1:]
    if action in ("add", "remove") and not tags:
        parser.error(f"'{action}' needs at least one tag name")
    return paths, action, tags


def main() -> int:
    paths, action, tags = parse_args(sys.argv[1:])

    missing = [path for path in paths if not path.exists()]
    if missing:
        for path in missing:
            print(f"findertag: no such file or directory: {path}", file=sys.stderr)
        return 1

    touched = [path for path in paths if apply_action(path, action, tags)]

    if action != "list" and touched:
        # mdls / mdfind への反映を促す（それでも数秒のラグは残る）
        subprocess.run(["mdimport", *[str(path) for path in touched]], check=False)
    return 0 if len(touched) == len(paths) else 1


if __name__ == "__main__":
    sys.exit(main())
