#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Apple Mail のメール（.emlx）から添付ファイルを取り出して保存する。

`~/bin/mailsearch --json ...` の各ヒットに含まれる `path`（.emlx の絶対パス）を
そのまま渡す。Apple Mail アプリを起動せず、ディスク上の .emlx を直接パースする
ため高速。既定の保存先は整理用 Inbox（`~/Documents/cowork/Inbox`）。

使用例:
  # mailsearch で見つけたメールの添付を Inbox に保存
  mail_save_attachments.py "/path/to/Messages/925871.emlx"

  # 中身を見るだけ（保存しない）
  mail_save_attachments.py --list "/path/to/....emlx"

  # 保存先を指定
  mail_save_attachments.py --dest ~/Desktop "/path/to/....emlx"

mailsearch と組み合わせる例:
  ~/bin/mailsearch --json --limit 1 --sort date-desc -r ~/Library/Mail/V10 贈与 \
    | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["path"])' \
    | xargs -I{} mail_save_attachments.py "{}"

ファイル名について:
  添付名が正しくデコードできればその名前で保存する。Outlook 由来の壊れた
  iso-2022-jp エンコード等でデコードに失敗した場合は、**メールの件名**をもとに
  した名前（例: `贈与等報告書確認依頼.xlsx`）で保存する。いずれにせよ Inbox 格納後、
  `ファイル整理.md` のルールに従って内容に応じた日本語名へ改名する前提。

注意:
  - `.partial.emlx`（IMAP で本文/添付が未ダウンロード）は中身が取れないことがある。
    その場合は Apple Mail で該当メールを一度開いて完全取得してから再実行する。
  - 既定では inline パート（署名画像など）は除外する。含めるには --include-inline。
  - 同名ファイルは上書きせず `_2`, `_3` … を付ける。
"""

from __future__ import annotations

import argparse
import email
import mimetypes
import re
import sys
import unicodedata
from email import policy
from email.header import decode_header
from pathlib import Path

DEFAULT_DEST = Path("~/Documents/cowork/Inbox").expanduser()


def decode_name(raw: str | None) -> str | None:
    """RFC2047 エンコードされたファイル名をデコードする（複数コーデックを試行）。"""
    if not raw or "=?" not in raw:
        return raw
    out: list[str] = []
    for data, enc in decode_header(raw):
        if isinstance(data, bytes):
            codecs = ([enc] if enc else []) + ["utf-8", "iso-2022-jp-ext", "cp50220"]
            for codec in codecs:
                try:
                    out.append(data.decode(codec))
                    break
                except Exception:
                    continue
            else:
                out.append(data.decode("utf-8", errors="replace"))
        else:
            out.append(data)
    return "".join(out)


def looks_broken(name: str | None) -> bool:
    """デコード後の名前が文字化け/壊れているかを判定する。"""
    if not name:
        return True
    if "�" in name:  # 置換文字
        return True
    if any(ord(c) < 0x20 for c in name):  # 制御文字（ESC 等の残骸）
        return True
    if re.search(r"\$B|\(B|=\?", name):  # 漏れた iso-2022-jp エスケープ / 未デコード
        return True
    return False


def sanitize(name: str) -> str:
    name = unicodedata.normalize("NFC", name).strip()
    name = name.replace("/", "_").replace(":", "_").replace("\x00", "")
    name = name.lstrip(".")
    name = re.sub(r"\s+", " ", name)
    return name or "attachment"


def guess_ext(filename: str | None, content_type: str) -> str:
    if filename:
        ext = Path(filename).suffix
        if ext:
            return ext
    return mimetypes.guess_extension(content_type) or ".bin"


def unique_path(dest: Path, name: str) -> Path:
    target = dest / name
    if not target.exists():
        return target
    stem, suffix = Path(name).stem, Path(name).suffix
    i = 2
    while (dest / f"{stem}_{i}{suffix}").exists():
        i += 1
    return dest / f"{stem}_{i}{suffix}"


def load_message(path: Path):
    raw = path.read_bytes()
    # .emlx は「先頭行=バイト数 → RFC822 → 末尾 plist」形式。先頭行を落とす。
    body = raw[raw.index(b"\n") + 1:]
    return email.message_from_bytes(body, policy=policy.default)


def iter_attachments(msg, include_inline: bool):
    """(元ファイル名, content_type, payload bytes) を列挙する。"""
    for part in msg.walk():
        if part.is_multipart():
            continue
        disp = part.get_content_disposition()
        fn = part.get_filename()
        is_attachment = disp == "attachment" or (fn is not None)
        if disp == "inline" and not include_inline:
            continue
        if not is_attachment:
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            yield (fn, part.get_content_type(), None)
            continue
        yield (fn, part.get_content_type(), payload)


def process(path: Path, dest: Path, subject: str, list_only: bool,
            include_inline: bool) -> int:
    msg = load_message(path)
    subj = sanitize(decode_name(msg["subject"]) or subject or "attachment")
    partial = path.name.endswith(".partial.emlx")
    if partial:
        print(f"  ⚠ {path.name} は .partial（未ダウンロード）。添付が取れない場合は "
              f"Apple Mail で開いてから再実行してください。", file=sys.stderr)

    saved = 0
    idx = 0
    for fn, ctype, payload in iter_attachments(msg, include_inline):
        idx += 1
        decoded = decode_name(fn)
        if decoded and not looks_broken(decoded):
            name = sanitize(decoded)
        else:
            ext = guess_ext(fn, ctype)
            name = f"{subj}{ext}"
        if payload is None:
            print(f"  [取得不可] {name}（本文なし/partial）", file=sys.stderr)
            continue
        if list_only:
            print(f"  [{idx}] {name}  ({len(payload):,} bytes, {ctype})")
            saved += 1
            continue
        target = unique_path(dest, name)
        target.write_bytes(payload)
        print(f"  保存: {target}  ({len(payload):,} bytes)")
        saved += 1
    if saved == 0:
        print("  添付なし", file=sys.stderr)
    return saved


def main() -> int:
    p = argparse.ArgumentParser(
        description="Apple Mail の .emlx から添付を保存する（Inbox 既定）。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("paths", nargs="+", help=".emlx の絶対パス（mailsearch の path）")
    p.add_argument("--dest", type=Path, default=DEFAULT_DEST,
                   help=f"保存先ディレクトリ（既定: {DEFAULT_DEST}）")
    p.add_argument("--list", action="store_true", dest="list_only",
                   help="保存せず添付を一覧表示")
    p.add_argument("--include-inline", action="store_true",
                   help="inline パート（署名画像など）も含める")
    args = p.parse_args()

    dest = args.dest.expanduser()
    if not args.list_only:
        if not dest.is_dir():
            p.error(f"保存先が存在しません: {dest}")

    total = 0
    for sp in args.paths:
        path = Path(sp).expanduser()
        if not path.is_file():
            print(f"ファイルがありません: {path}", file=sys.stderr)
            continue
        print(f"● {path.name}")
        total += process(path, dest, subject="", list_only=args.list_only,
                         include_inline=args.include_inline)
    print(f"\n{'一覧' if args.list_only else '保存'}: 合計 {total} 件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
