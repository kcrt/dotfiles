#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Apple Mail の下書きを作成する (new / reply / reply-all / forward)。

macOS の Apple Mail を AppleScript(osascript)経由で操作し、宛先・本文・
添付ファイル付きのメールを **下書き（Draft）として保存** する。
**送信は絶対に行わない**（save のみ。send は呼ばない）。

reply / reply-all / forward は元メールを Message-ID または件名で特定する。
Message-ID は `~/bin/mailsearch --json ...` の出力（`<...>` は省略可）が使える。

使用例:
  # 新規作成
  apple_mail_draft.py new --to alice@example.com --subject "件名" \
      --body "本文" --attach ~/a.pdf --attach ~/b.pdf

  # 返信（元メールへの Reply として作成。宛先は自動）
  apple_mail_draft.py reply --message-id "ABC@example.com" \
      --body "本文" --attach ~/reply.pdf

  # 全員に返信
  apple_mail_draft.py reply --all --message-id "ABC@example.com" --body "本文"

  # 転送（転送先は --to で指定）
  apple_mail_draft.py forward --message-id "ABC@example.com" \
      --to bob@example.com --body "本文" --attach ~/doc.pdf

本文について:
  - reply/reply-all は Mail のネイティブ引用（元メールの引用＋署名）を活かす。
    返信ウィンドウ・宛先・添付までを用意し、**本文はクリップボードに載せるだけ
    （pbcopy 相当）** で、ユーザーが本文欄の先頭で ⌘V で手貼りする。自動 ⌘V は
    環境（アクセシビリティ権限・タイミング）で不発になることがあるため行わない。
    `set content` を使わないのは、本文が cite ブロック（<blockquote type="cite">）に
    巻き込まれ送信時に本文全体が "> " 付き引用として送られてしまう Mail の挙動を
    回避するため（下記「既知の落とし穴」）。
    引用を残したくない場合は --no-quote を付ける（この場合はユーザーが本文欄で
    ⌘A→⌘V し、ネイティブ引用ごと本文に置き換える）。
    （--keep-quote は後方互換のため受理するが、既定動作なので何もしない。）
  - forward は Mail が生成する本文（元メール＋添付）を活かし、その上に本文を
    差し込む（従来どおり set content。転送はウィンドウの初期フォーカスが宛先欄の
    ため貼り付け方式は使わない）。
  - 署名は Apple Mail の設定に従い保存時に自動付与される。

既知の落とし穴（なぜ reply は貼り付け方式なのか）:
  - AppleScript で outgoing message の `content` をセットすると、Mail(16 系)は
    本文を `Apple-Mail-URLShareWrapperClass` 内の `<blockquote type="cite">` で
    包む。プレーンテキストとして送信される段でこの cite ブロックが各行 "> " に
    変換され、返信本文そのものが引用扱いで相手に届く（受信側 Gmail 等では本文が
    グレーの引用として畳まれて読みにくい）。
  - 手打ち（GUI 入力）や貼り付けで入れた本文は cite ブロックに入らず、通常の
    `<div>`（＝引用なし）になる。キーストローク直打ちは日本語が IME で化けるため、
    クリップボード貼り付けを使う（貼り付けは IME を経由せず Unicode をそのまま挿入）。
  - この方式はスレッド連結（In-Reply-To/References）を維持したまま、標準テキストの
    クリーンな本文になる。⇧⌘T の手動変換は不要。

書式について:
  - new は Mail の既定フォーマット（Settings > Composing）に従う。
  - reply は上記のとおり本文を貼り付けるため、元メールが HTML でも本文部分は
    プレーンテキスト（引用なし）になる。

補足:
  - reply/reply-all は **作成ウィンドウを開く**（一瞬前面に出る）。作成後の
    ウィンドウは本文欄にフォーカスした状態で開いたまま残す（ユーザーが ⌘V で
    本文を貼り、内容確認 → 送信できる）。返信ウィンドウが開くまでポーリングし、
    開かなければ中止する。
  - **本文はクリップボードに載せたまま**にする（ユーザーが手貼りするので復元しない）。
    クリップボードの内容を上書きするため、reply/reply-all を実行する側（Claude 等）は
    「今から実行します。準備 OK か」をユーザーに確認してから起動すること
    （ユーザーが別作業でクリップボードを使っている最中を避ける）。
  - 元メールは既定で INBOX を検索する。見つからない場合は --search-all で
    全メールボックスを走査する。
  - --open は互換のため受理する（reply は元々ウィンドウを開く）。
  - --dry-run で実行せず生成した AppleScript を表示する。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


def as_lit(s: str) -> str:
    """Python 文字列を AppleScript の文字列リテラル本体へエスケープする。

    バックスラッシュとダブルクオートのみをエスケープし、改行はそのまま残す
    （osascript にファイルとして渡す場合、リテラル内の改行は有効）。
    """
    return s.replace("\\", "\\\\").replace('"', '\\"')


def recipients_block(kind: str, addresses: list[str]) -> str:
    """to / cc / bcc recipient を追加する AppleScript 断片を生成する。"""
    lines = []
    for addr in addresses:
        lines.append(
            f'\t\tmake new {kind} recipient at end of {kind} recipients '
            f'with properties {{address:"{as_lit(addr)}"}}'
        )
    return "\n".join(lines)


def attachments_block(paths: list[str]) -> str:
    """添付を追加する AppleScript 断片を生成する。

    本文を設定した後に「最後の段落の後」へ挿入する。添付挿入で本文が消える
    Mail の不具合を避けるため、本文設定 → delay → 添付 の順で呼び出すこと。
    """
    lines = []
    for p in paths:
        abspath = str(Path(p).expanduser().resolve())
        lines.append(
            f'\ttell msg to make new attachment with properties '
            f'{{file name:(POSIX file "{as_lit(abspath)}")}} '
            f'at after the last paragraph of content'
        )
        lines.append("\tdelay 1")
    return "\n".join(lines)


def find_original_block(message_id: str | None, subject: str | None, search_all: bool) -> str:
    """元メールを特定して変数 orig に束縛する AppleScript 断片を生成する。"""
    if message_id:
        mid = as_lit(message_id.strip().lstrip("<").rstrip(">"))
        cond = f'message id is "{mid}"'
        label = f"message-id {mid}"
    elif subject:
        cond = f'subject contains "{as_lit(subject)}"'
        label = f"subject~{subject}"
    else:
        raise ValueError("reply/forward には --message-id か --match-subject が必要です")

    lines = [f"\tset matches to (messages of inbox whose {cond})"]
    if search_all:
        lines += [
            "\tif (count of matches) is 0 then",
            "\t\trepeat with acct in accounts",
            "\t\t\trepeat with mb in (mailboxes of acct)",
            "\t\t\t\ttry",
            f"\t\t\t\t\tset hits to (messages of mb whose {cond})",
            "\t\t\t\t\tif (count of hits) > 0 then",
            "\t\t\t\t\t\tset matches to hits",
            "\t\t\t\t\t\texit repeat",
            "\t\t\t\t\tend if",
            "\t\t\t\tend try",
            "\t\t\tend repeat",
            "\t\t\tif (count of matches) > 0 then exit repeat",
            "\t\tend repeat",
            "\tend if",
        ]
    lines += [
        f'\tif (count of matches) is 0 then error "元メールが見つかりません: {as_lit(label)}"',
        "\tset orig to item 1 of matches",
    ]
    return "\n".join(lines)


def build_new(args) -> str:
    vis = "true" if args.open else "false"
    body = as_lit(args.body)
    subject = as_lit(args.subject)
    parts = ['tell application "Mail"']
    parts.append(
        f'\tset msg to make new outgoing message with properties '
        f'{{subject:"{subject}", content:"{body}", visible:{vis}}}'
    )
    parts.append("\ttell msg")
    rblocks = []
    if args.to:
        rblocks.append(recipients_block("to", args.to))
    if args.cc:
        rblocks.append(recipients_block("cc", args.cc))
    if args.bcc:
        rblocks.append(recipients_block("bcc", args.bcc))
    parts.extend(rblocks)
    parts.append("\tend tell")
    if args.sender:
        parts.append(f'\tset sender of msg to "{as_lit(args.sender)}"')
    parts.append("\tdelay 1")
    if args.attach:
        parts.append(attachments_block(args.attach))
    parts.append("\tsave msg")
    parts.append('\treturn "OK(new) subject=" & (subject of msg)')
    parts.append("end tell")
    return "\n".join(parts)


def _recipients_and_subject(args) -> list[str]:
    """追加宛先と件名変更の AppleScript 断片（末尾の Mail tell 内で使う）を返す。"""
    parts: list[str] = []
    tell_lines = []
    if args.to:
        tell_lines.append(recipients_block("to", args.to))
    if args.cc:
        tell_lines.append(recipients_block("cc", args.cc))
    if args.bcc:
        tell_lines.append(recipients_block("bcc", args.bcc))
    if tell_lines:
        parts.append("\ttell msg")
        parts.extend(tell_lines)
        parts.append("\tend tell")
    if args.subject:
        parts.append(f'\tset subject of msg to "{as_lit(args.subject)}"')
    return parts


def build_reply(args, reply_all: bool) -> str:
    """reply / reply-all の下書きを作る。

    本文は**クリップボードに載せるだけ（pbcopy 相当）**。返信ウィンドウを開いて
    ネイティブ引用・スレッド連結・宛先・添付までを用意し、本文はユーザーが
    ⌘V で手貼りする。System Events による自動 ⌘V は環境（アクセシビリティ権限・
    タイミング）で不発になることがあるため行わない。
    `set content` を使わないのは、本文が cite ブロックに巻き込まれ送信時に本文全体が
    "> " 付き引用になってしまう Mail の挙動を回避するため（docstring「既知の落とし穴」）。
    ネイティブ引用と In-Reply-To/References は維持される。
    """
    body = as_lit(args.body)
    verb = "reply orig with reply to all" if reply_all else "reply orig"
    mode = "reply-all" if reply_all else "reply"

    parts = ['tell application "Mail"']
    parts.append(find_original_block(args.message_id, args.match_subject, args.search_all))
    # 返信ウィンドウの出現を検知するため、開く前のウィンドウ数を控える。
    parts.append("\tset winBefore to (count windows)")
    parts.append("end tell")

    # 本文をクリップボードへ（ユーザーが手貼りするので復元はしない）。
    parts.append(f'set the clipboard to "{body}"')

    # 返信ウィンドウを開く（ネイティブ引用＋署名＋スレッド連結を生成させる）。
    parts.append('tell application "Mail"')
    parts.append("\tactivate")
    parts.append(f"\tset msg to {verb}")
    parts.append("end tell")

    # 実際に返信ウィンドウが開くまでポーリングする（最大 ~10 秒）。
    parts.append("set opened to false")
    parts.append("repeat 40 times")
    parts.append("\ttell application \"Mail\" to set winNow to (count windows)")
    parts.append("\tif winNow > winBefore then")
    parts.append("\t\tset opened to true")
    parts.append("\t\texit repeat")
    parts.append("\tend if")
    parts.append("\tdelay 0.25")
    parts.append("end repeat")
    parts.append('if not opened then error "返信ウィンドウが開きませんでした"')
    # 引用/署名の生成が落ち着くのを待つ。
    parts.append("delay 0.8")

    # 追加宛先・件名・添付・保存（本文は入れない）。
    parts.append('tell application "Mail"')
    parts.extend(_recipients_and_subject(args))
    if args.attach:
        parts.append(attachments_block(args.attach))
    parts.append("\tset outSubject to (subject of msg) as string")
    parts.append("\tsave msg")
    parts.append("end tell")

    # Mail を前面化し、本文欄にフォーカスした状態でユーザーへ渡す（すぐ ⌘V できる）。
    parts.append('try')
    parts.append('\ttell application "System Events" to set frontmost of process "Mail" to true')
    parts.append('end try')

    hint = "本文欄で ⌘A → ⌘V" if args.no_quote else "本文欄の先頭で ⌘V"
    parts.append(
        f'return "OK({mode}) 本文はクリップボードにコピー済み。開いた返信ウィンドウの'
        f'{hint} で貼り付けてください。 subject=" & outSubject'
    )
    return "\n".join(parts)


def build_forward(args) -> str:
    """転送の下書きを作る（Mail 生成の転送本文の上に本文を差し込む）。"""
    body = as_lit(args.body)
    parts = ['tell application "Mail"']
    parts.append(find_original_block(args.message_id, args.match_subject, args.search_all))
    parts.append("\tset msg to forward orig without opening window")
    # forward が非同期に生成する本文（元メール＋添付）が set content を上書き
    # するため待つ。
    parts.append("\tdelay 2")
    if args.no_quote:
        parts.append(f'\tset content of msg to "{body}"')
    else:
        parts.append(f'\tset content of msg to "{body}" & return & (content of msg)')
    parts.append("\tdelay 1")

    parts.extend(_recipients_and_subject(args))

    if args.attach:
        parts.append(attachments_block(args.attach))

    parts.append("\tsave msg")
    parts.append('\treturn "OK(forward) subject=" & (subject of msg)')
    parts.append("end tell")
    return "\n".join(parts)


def run_applescript(script: str) -> str:
    with tempfile.NamedTemporaryFile(
        "w", suffix=".applescript", delete=False, encoding="utf-8"
    ) as f:
        f.write(script)
        path = f.name
    try:
        proc = subprocess.run(
            ["osascript", path], capture_output=True, text=True
        )
    finally:
        Path(path).unlink(missing_ok=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "osascript failed")
    return proc.stdout.strip()


def resolve_body(args) -> None:
    """--body-file が指定されていれば読み込み args.body に格納する。"""
    if getattr(args, "body_file", None):
        args.body = Path(args.body_file).expanduser().read_text(encoding="utf-8")
    if args.body is None:
        args.body = ""


def add_common(sp, *, need_subject: bool) -> None:
    sp.add_argument("--to", action="append", default=[], help="宛先(複数指定可)")
    sp.add_argument("--cc", action="append", default=[], help="CC(複数指定可)")
    sp.add_argument("--bcc", action="append", default=[], help="BCC(複数指定可)")
    sp.add_argument("--subject", required=need_subject, help="件名")
    sp.add_argument("--body", help="本文(文字列)")
    sp.add_argument("--body-file", help="本文をファイルから読む")
    sp.add_argument("--attach", action="append", default=[], help="添付ファイル(複数指定可)")
    sp.add_argument("--open", action="store_true", help="下書きウィンドウを表示する")
    sp.add_argument("--dry-run", action="store_true", help="実行せず AppleScript を表示")


def add_target(sp) -> None:
    g = sp.add_mutually_exclusive_group(required=True)
    g.add_argument("--message-id", help="元メールの Message-ID (<> は省略可)")
    g.add_argument("--match-subject", help="元メールを件名の部分一致で特定")
    sp.add_argument("--search-all", action="store_true",
                    help="INBOX で見つからない場合に全メールボックスを検索")
    sp.add_argument("--no-quote", action="store_true",
                    help="元メールの引用文を残さず本文だけに置き換える")
    # 後方互換: 以前は既定で引用を消していたため --keep-quote が必要だった。
    # 現在は引用を残すのが既定なので、--keep-quote は受理するだけの no-op。
    sp.add_argument("--keep-quote", action="store_true", help=argparse.SUPPRESS)


def main() -> int:
    p = argparse.ArgumentParser(
        description="Apple Mail の下書きを作成する(送信はしない)。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="mode", required=True)

    sp_new = sub.add_parser("new", help="新規メールの下書き")
    add_common(sp_new, need_subject=True)
    sp_new.add_argument("--from", dest="sender",
                        help='差出人アカウント 例: "Name <a@example.com>"')

    sp_reply = sub.add_parser("reply", help="返信の下書き(--all で全員に返信)")
    sp_reply.add_argument("--all", action="store_true", help="全員に返信")
    add_target(sp_reply)
    add_common(sp_reply, need_subject=False)
    sp_reply.add_argument("--from", dest="sender", help=argparse.SUPPRESS)

    sp_fwd = sub.add_parser("forward", help="転送の下書き(--to で転送先)")
    add_target(sp_fwd)
    add_common(sp_fwd, need_subject=False)
    sp_fwd.add_argument("--from", dest="sender", help=argparse.SUPPRESS)

    args = p.parse_args()
    resolve_body(args)

    if args.mode == "new":
        if not args.to:
            p.error("new には --to が必要です")
        script = build_new(args)
    elif args.mode == "reply":
        script = build_reply(args, args.all)
    elif args.mode == "forward":
        if not args.to:
            p.error("forward には --to(転送先)が必要です")
        script = build_forward(args)
    else:  # pragma: no cover
        p.error(f"unknown mode: {args.mode}")

    if args.dry_run:
        print(script)
        return 0

    try:
        print(run_applescript(script))
    except RuntimeError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
