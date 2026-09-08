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
  - `.partial.emlx`（IMAP で本文/添付が未ダウンロード）はディスク上に中身が無い。
    その場合は **Apple Mail 経由で自動的に回収する**（Message-ID で該当メールを引き、
    `source` で完全取得させてから Mail に添付を書き出させる）。Mail は壊れた
    iso-2022-jp のファイル名も正しくデコードするので、名前もこちらの方が良い。
    ⚠️ この経路は Apple Mail を（起動していなければ）起動する。使いたくないときは
    `--no-mail-fallback` を付ける。
  - 既定では inline パート（署名画像など）は除外する。含めるには --include-inline。
  - 同名ファイルは上書きせず `_2`, `_3` … を付ける。
"""

from __future__ import annotations

import argparse
import email
import mimetypes
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from email import policy
from email.header import decode_header
from pathlib import Path

DEFAULT_DEST = Path("~/Documents/cowork/Inbox").expanduser()

# Apple Mail 経由の回収に許す時間。メールボックスを絞れば数秒で終わるが、
# 最後の手段の全メールボックス走査は 2 分を超えることがある（実測）。
MAIL_TIMEOUT_SEC = 300

# 該当メールが Mail 上に見つからなかったことを表す AppleScript の戻り値。
NOT_FOUND = "NOTFOUND"


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


def inline_names(msg) -> set[str]:
    """inline パート（署名画像など）のファイル名を集める。

    Mail 経由で回収するときは、どれが inline かを AppleScript 側から判別できない
    （`mail attachment` に disposition が無い）ため、ローカルの MIME 構造から
    名前で照合して除外する。
    """
    names: set[str] = set()
    for part in msg.walk():
        if part.is_multipart() or part.get_content_disposition() != "inline":
            continue
        raw = part.get_filename()
        for candidate in (raw, decode_name(raw)):
            if candidate:
                names.add(candidate)
                names.add(sanitize(candidate))
    return names


def mailbox_name_from_path(path: Path) -> str | None:
    """.emlx のパスから Apple Mail のメールボックス名を推定する。

    パスは …/V10/<アカウントUUID>/INBOX.mbox/Archive.mbox/<UUID>/Data/…/Messages/N.emlx
    のように、メールボックスの入れ子が `.mbox` ディレクトリで表される。末尾の
    `.mbox` が実際のメールボックス（INBOX / Archive / Sent / Scan …）にあたる。
    ここで絞れるかどうかが速さを決める（絞れば数秒、全走査は 2 分超）。
    """
    boxes = [part.removesuffix(".mbox") for part in path.parts if part.endswith(".mbox")]
    return boxes[-1] if boxes else None


def applescript_literal(value: str) -> str:
    """文字列を AppleScript のリテラルにする。"""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def build_fetch_script(message_id: str, mailbox: str | None,
                       save_dir: Path | None) -> str:
    """添付を Mail に書き出させる AppleScript を組み立てる。

    `mailbox` を指定すると各アカウントのそのメールボックスだけを見る（速い）。
    None のときは全メールボックスを走査する（最後の手段）。
    `save_dir` が None なら書き出さず、名前とサイズだけを返す（--list 用）。
    """
    if mailbox:
        lookup = f"""            try
                set ms to (messages of mailbox {applescript_literal(mailbox)} of acct whose message id is mid)
                if (count of ms) > 0 then set found to item 1 of ms
            end try"""
    else:
        lookup = """            repeat with mb in every mailbox of acct
                if found is missing value then
                    try
                        set ms to (messages of mb whose message id is mid)
                        if (count of ms) > 0 then set found to item 1 of ms
                    end try
                end if
            end repeat"""

    save = ""
    if save_dir is not None:
        prefix = applescript_literal(f"{save_dir}/")
        save = f"""        try
            save a in (POSIX file ({prefix} & n))
        end try
"""

    return f"""tell application "Mail"
    set mid to {applescript_literal(message_id)}
    set found to missing value
    repeat with acct in every account
        if found is missing value then
{lookup}
        end if
    end repeat
    if found is missing value then return {applescript_literal(NOT_FOUND)}
    -- source へのアクセスが本文・添付の完全ダウンロードを促す（メールを開かずに済む）。
    set s to source of found
    set out to ""
    repeat with a in (every mail attachment of found)
        set n to name of a
{save}        set out to out & n & tab & (file size of a as string) & linefeed
    end repeat
    return out
end tell"""


def run_osascript(script: str) -> str:
    """osascript を実行して標準出力を返す。失敗は RuntimeError。"""
    proc = subprocess.run(["osascript", "-e", script], capture_output=True,
                          text=True, timeout=MAIL_TIMEOUT_SEC)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "osascript が失敗しました")
    return proc.stdout


def parse_fetch_output(out: str) -> list[tuple[str, int]]:
    """AppleScript の「名前<TAB>バイト数」出力を解析する。"""
    found: list[tuple[str, int]] = []
    for line in out.splitlines():
        name, _, size = line.rpartition("\t")
        if not name:
            continue
        try:
            found.append((name, int(size)))
        except ValueError:
            found.append((name, 0))
    return found


def fetch_from_mail(message_id: str, mailbox: str | None,
                    save_dir: Path | None) -> list[tuple[str, int]] | None:
    """Apple Mail に添付を書き出させ、(ファイル名, バイト数) を返す。

    見つからなければ None。パスから絞ったメールボックスを先に試し、外れたときだけ
    全メールボックス走査に落ちる。
    """
    attempts: list[str | None] = [mailbox, None] if mailbox else [None]
    for attempt in attempts:
        if attempt is None and mailbox:
            print("  … 指定のメールボックスに無いため全メールボックスを走査します"
                  "（数分かかることがあります）", file=sys.stderr)
        out = run_osascript(build_fetch_script(message_id, attempt, save_dir))
        if out.strip() != NOT_FOUND:
            return parse_fetch_output(out)
    return None


def recover_via_mail(path: Path, msg, dest: Path, list_only: bool,
                     include_inline: bool, done_names: set[str]) -> int:
    """.partial で取れなかった添付を Apple Mail 経由で回収する。

    ディスク上の .partial.emlx は Mail が完全取得しても即座には更新されないため、
    Mail 自身に書き出させる（`ファイル整理.md` の Scanメール手順と同じ手筋）。
    Mail 側のファイル名は壊れた iso-2022-jp も正しくデコードされているので、
    ローカルの decode_name より良い名前が得られる。
    """
    message_id = (msg["message-id"] or "").strip().strip("<>")
    if not message_id:
        print("  [取得不可] Message-ID が無いため Mail から回収できません", file=sys.stderr)
        return 0

    mailbox = mailbox_name_from_path(path)
    skip = set() if include_inline else inline_names(msg)

    with tempfile.TemporaryDirectory(prefix="mail_att_") as tmp:
        tmpdir = Path(tmp)
        try:
            found = fetch_from_mail(message_id, mailbox, None if list_only else tmpdir)
        except (RuntimeError, subprocess.TimeoutExpired) as err:
            print(f"  [取得不可] Mail 経由の回収に失敗しました: {err}", file=sys.stderr)
            return 0
        if found is None:
            print(f"  [取得不可] Mail 上に Message-ID <{message_id}> が見つかりません",
                  file=sys.stderr)
            return 0

        count = 0
        for name, size in found:
            clean = sanitize(name)
            if name in skip or clean in skip or clean in done_names:
                continue
            if list_only:
                print(f"  [Mail] {clean}  ({size:,} bytes)")
                count += 1
                continue
            source = tmpdir / name
            if not source.is_file():
                print(f"  [取得不可] {clean}（Mail が書き出せませんでした）", file=sys.stderr)
                continue
            target = unique_path(dest, clean)
            shutil.move(str(source), target)
            print(f"  保存: {target}  ({target.stat().st_size:,} bytes, Mail 経由)")
            count += 1
        return count


def process(path: Path, dest: Path, subject: str, list_only: bool,
            include_inline: bool, mail_fallback: bool) -> int:
    msg = load_message(path)
    subj = sanitize(decode_name(msg["subject"]) or subject or "attachment")

    saved = 0
    idx = 0
    missing = 0
    # Mail 経由で回収したときに二重取得しないよう、ここで書き出した名前を覚える。
    done_names: set[str] = set()
    for fn, ctype, payload in iter_attachments(msg, include_inline):
        idx += 1
        decoded = decode_name(fn)
        if decoded and not looks_broken(decoded):
            name = sanitize(decoded)
        else:
            ext = guess_ext(fn, ctype)
            name = f"{subj}{ext}"
        # .partial では payload が None か空になる（パート構造と名前だけが残る）。
        if not payload:
            missing += 1
            continue
        if list_only:
            print(f"  [{idx}] {name}  ({len(payload):,} bytes, {ctype})")
            done_names.add(name)
            saved += 1
            continue
        target = unique_path(dest, name)
        target.write_bytes(payload)
        print(f"  保存: {target}  ({len(payload):,} bytes)")
        done_names.add(name)
        saved += 1

    if missing:
        if mail_fallback:
            print(f"  ⚠ {missing} 件が未ダウンロード（.partial）。Apple Mail から回収します。",
                  file=sys.stderr)
            saved += recover_via_mail(path, msg, dest, list_only, include_inline,
                                      done_names)
        else:
            print(f"  [取得不可] {missing} 件が未ダウンロード（.partial）。"
                  f"--no-mail-fallback を外すか、Apple Mail で開いてから再実行してください。",
                  file=sys.stderr)

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
    p.add_argument("--no-mail-fallback", action="store_false", dest="mail_fallback",
                   help=".partial の添付を Apple Mail 経由で回収しない（Mail を起動させない）")
    args = p.parse_args()

    # 進捗（stdout）と警告（stderr）が混ざったときに順序が入れ替わらないようにする。
    sys.stdout.reconfigure(line_buffering=True)

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
                         include_inline=args.include_inline,
                         mail_fallback=args.mail_fallback)
    print(f"\n{'一覧' if args.list_only else '保存'}: 合計 {total} 件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
