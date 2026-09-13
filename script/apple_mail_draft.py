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
  - reply / reply-all / forward はいずれも Mail のネイティブな本文（元メールの引用
    ＋署名、転送なら元メール＋添付）を活かす。作成ウィンドウ・宛先・添付までを
    用意し、**本文はクリップボードに載せるだけ（pbcopy 相当）** で、ユーザーが
    本文欄の先頭で ⌘V で手貼りする。自動 ⌘V は環境（アクセシビリティ権限・
    タイミング）で不発になることがあるため行わない。
    `set content` を使わないのは、本文が cite ブロック（<blockquote type="cite">）に
    巻き込まれ送信時に本文全体が "> " 付き引用として送られてしまう Mail の挙動を
    回避するため（下記「既知の落とし穴」）。
  - reply/reply-all で引用を残したくない場合は --no-quote を付ける（この場合は
    ユーザーが本文欄で ⌘A→⌘V し、ネイティブ引用ごと本文に置き換える）。
    **forward では --no-quote は使えない**（転送は元メールの引用が本体のため）。
    （--keep-quote は後方互換のため受理するが、既定動作なので何もしない。）
  - new だけは従来どおり content プロパティで本文を入れる（ウィンドウを開かない
    運用のため。下記 cite 巻き込みは未対応）。
  - 署名は Apple Mail の設定に従い保存時に自動付与される。

既知の落とし穴（なぜ貼り付け方式なのか）:
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
  - reply/forward は上記のとおり本文を貼り付けるため、元メールが HTML でも
    貼り付けた本文部分はプレーンテキスト（引用なし）になる。

補足:
  - reply / reply-all / forward は **作成ウィンドウを開く**（一瞬前面に出る）。作成後の
    ウィンドウは本文欄にフォーカスした状態で開いたまま残す（ユーザーが ⌘V で
    本文を貼り、内容確認 → 送信できる）。ウィンドウが開くまでポーリングし、
    開かなければ中止する。
  - 返信ウィンドウは初期フォーカスが本文欄だが、**転送ウィンドウは宛先欄**なので、
    転送のときだけ System Events で本文欄へフォーカスを移し ⌘↑ で先頭へ寄せる。
    失敗しても下書きは壊さず、戻り値の案内が「本文欄をクリックしてから ⌘V」に
    切り替わる。
  - **本文はクリップボードに載せたまま**にする（ユーザーが手貼りするので復元しない）。
    クリップボードの内容を上書きするため、reply/reply-all/forward を実行する側
    （Claude 等）は「今から実行します。準備 OK か」をユーザーに確認してから起動する
    こと（ユーザーが別作業でクリップボードを使っている最中を避ける）。
  - 元メールは既定で INBOX を検索する。見つからない場合は --search-all で
    全メールボックスを走査する。
  - --open は互換のため受理する（reply/forward は元々ウィンドウを開く）。
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


def _focus_body_block() -> list[str]:
    """作成ウィンドウの本文欄へフォーカスを移す AppleScript 断片を返す。

    転送ウィンドウは初期フォーカスが**宛先欄**なので、そのままだとユーザーの ⌘V が
    宛先欄へ入ってしまう。本文欄（スクロールエリア）の AXFocused を立てて移し、
    ⌘↑ で本文の先頭へ寄せる。アクセシビリティ権限が無い等で失敗しても下書きを
    壊さないよう try で囲み、成否を focusOK に残して案内文（hintText）を切り替える。

    ⚠️ **成否は「宛先欄からフォーカスが外れたか」で判定する。** 本文欄の実体は
    AXWebArea で、フォーカスが当たっていても AXFocused の読み戻しは常に false を
    返す（2026-09-13 実測）ので、そちらでは判定できない。宛先欄が最初のテキスト
    フィールドでなくなるような UI 変更が起きた場合は before が false になり、
    focusOK も false 側（＝ユーザーに本文欄をクリックしてもらう案内）へ倒れる。
    """
    return [
        "delay 0.5",  # 件名を変えた場合にウィンドウのタイトルが追いつくのを待つ
        "try",
        '\ttell application "System Events" to tell process "Mail"',
        "\t\tset composeWin to first window whose name is outSubject",
        '\t\tset toFocusedBefore to (value of attribute "AXFocused" of (text field 1 of composeWin))',
        "\t\tset bodyArea to scroll area 1 of group 1 of group 1 of composeWin",
        '\t\tset value of attribute "AXFocused" of bodyArea to true',
        "\t\tdelay 0.4",
        '\t\tset toFocusedAfter to (value of attribute "AXFocused" of (text field 1 of composeWin))',
        "\t\tset focusOK to (toFocusedBefore and not toFocusedAfter)",
        "\t\tif focusOK then key code 126 using command down",  # ⌘↑ = 本文の先頭へ
        "\tend tell",
        "end try",
    ]


def _build_paste_draft(
    args,
    *,
    verb: str,
    mode: str,
    window_label: str,
    focus_body: bool,
    hint_block: list[str],
) -> str:
    """作成ウィンドウを開き、本文はクリップボードに載せるだけの下書きを作る。

    reply / reply-all / forward に共通の方式。Mail のネイティブな引用・スレッド連結・
    宛先・添付までを AppleScript で用意し、**本文はクリップボードに載せるだけ
    （pbcopy 相当）** で、ユーザーが ⌘V で手貼りする。System Events による自動 ⌘V は
    環境（アクセシビリティ権限・タイミング）で不発になることがあるため行わない。
    `set content` を使わないのは、本文が cite ブロックに巻き込まれ送信時に本文全体が
    "> " 付き引用になってしまう Mail の挙動を回避するため（docstring「既知の落とし穴」）。

    verb        … ウィンドウを開く AppleScript 断片（"reply orig" / "forward orig"）
    window_label… ウィンドウが開かなかったときのエラー文言（"返信" / "転送"）
    focus_body  … 開いた直後のフォーカスが本文欄でない（＝転送）ときに移す
    hint_block  … 戻り値へ載せる案内文を hintText に束縛する AppleScript 断片
    """
    body = as_lit(args.body)

    parts = ['tell application "Mail"']
    parts.append(find_original_block(args.message_id, args.match_subject, args.search_all))
    # 誤爆検知に使うため元メールの件名を控える（後段で outSubject と突き合わせる）。
    parts.append("\tset origSubject to (subject of orig) as string")
    # 作成ウィンドウの出現を検知するため、開く前のウィンドウ数を控える。
    parts.append("\tset winBefore to (count windows)")
    parts.append("end tell")

    # 本文をクリップボードへ（ユーザーが手貼りするので復元はしない）。
    parts.append(f'set the clipboard to "{body}"')

    # 作成ウィンドウを開く（ネイティブ引用＋署名＋スレッド連結を生成させる）。
    parts.append('tell application "Mail"')
    parts.append("\tactivate")
    parts.append(f"\tset msg to {verb}")
    parts.append("end tell")

    # 実際にウィンドウが開くまでポーリングする（最大 ~10 秒）。
    parts.append("set opened to false")
    parts.append("repeat 40 times")
    parts.append('\ttell application "Mail" to set winNow to (count windows)')
    parts.append("\tif winNow > winBefore then")
    parts.append("\t\tset opened to true")
    parts.append("\t\texit repeat")
    parts.append("\tend if")
    parts.append("\tdelay 0.25")
    parts.append("end repeat")
    parts.append(f'if not opened then error "{window_label}ウィンドウが開きませんでした"')
    # 引用/署名の生成が落ち着くのを待つ。
    parts.append("delay 0.8")

    # 追加宛先・件名・添付・保存（本文は入れない）。
    parts.append('tell application "Mail"')
    # 誤爆照合は --subject で上書きする前の「Mail が付けた件名」で行う。上書き後を
    # 見ると、別ウィンドウを掴んでいてもその件名が指定値に変わるだけで検知できない。
    parts.append("\tset nativeSubject to (subject of msg) as string")
    parts.extend(_recipients_and_subject(args))
    if args.attach:
        parts.append(attachments_block(args.attach))
    parts.append("\tset outSubject to (subject of msg) as string")
    parts.append("\tsave msg")
    parts.append("end tell")

    # Mail を前面化してユーザーへ渡す（そのまま ⌘V できる状態にする）。
    parts.append("set focusOK to false")
    parts.append("try")
    parts.append('\ttell application "System Events" to set frontmost of process "Mail" to true')
    parts.append("end try")
    if focus_body:
        parts.extend(_focus_body_block())
    parts.extend(hint_block)

    # 先頭に origSubject と nativeSubject を区切り付きで載せ、Python 側で件名照合して
    # から表示する。
    parts.append(
        f'return origSubject & "{SUBJECT_SEP}" & nativeSubject & "{SUBJECT_SEP}" & '
        f'"OK({mode}) 本文はクリップボードにコピー済み。" & hintText & '
        f'" subject=" & outSubject'
    )
    return "\n".join(parts)


def build_reply(args, reply_all: bool) -> str:
    """reply / reply-all の下書きを作る。

    返信ウィンドウは初期フォーカスが本文欄なので、フォーカス移動はしない。
    """
    hint = "本文欄で ⌘A → ⌘V" if args.no_quote else "本文欄の先頭で ⌘V"
    return _build_paste_draft(
        args,
        verb="reply orig with reply to all" if reply_all else "reply orig",
        mode="reply-all" if reply_all else "reply",
        window_label="返信",
        focus_body=False,
        hint_block=[f'set hintText to "開いた返信ウィンドウの{as_lit(hint)} で貼り付けてください。"'],
    )


def build_forward(args) -> str:
    """転送の下書きを作る。

    Mail のネイティブな転送本文（元メール＋添付）をそのまま活かし、その先頭へ
    ユーザーが本文を貼り付ける。転送ウィンドウは初期フォーカスが**宛先欄**なので、
    本文欄へフォーカスを移してから渡す（移せなかった場合は案内文で補う）。
    """
    return _build_paste_draft(
        args,
        verb="forward orig",
        mode="forward",
        window_label="転送",
        focus_body=True,
        hint_block=[
            'set hintText to "開いた転送ウィンドウの本文欄をクリックしてから ⌘V で貼り付けてください。"',
            'if focusOK then set hintText to '
            '"開いた転送ウィンドウの本文欄の先頭にフォーカス済みです。そのまま ⌘V で貼り付けてください。"',
        ],
    )


def count_outgoing_messages() -> int:
    """Mail に開かれている作成中メッセージの数を返す（取得できなければ -1）。"""
    proc = subprocess.run(
        ["osascript", "-e",
         'tell application "Mail" to return (count of outgoing messages)'],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return -1
    try:
        return int(proc.stdout.strip())
    except ValueError:
        return -1


def assert_no_open_drafts() -> None:
    """reply / reply-all / forward の誤爆ガード（2026-08-25 の実害を受けて追加）。

    `reply orig` / `forward orig` は、新規に開いた作成ウィンドウではなく **既に開いて
    いた別の作成中メッセージ**を掴むことがある。実際に別スレッドへ返信が作られ、
    そのまま送信された。元メールの特定（Message-ID 照合）は正しく動いていたので、
    ここでしか止められない。
    """
    n = count_outgoing_messages()
    if n == -1:
        print("警告: 作成中ウィンドウ数を取得できませんでした。Mail が起動しているか確認してください。",
              file=sys.stderr)
        return
    if n > 0:
        raise SystemExit(
            f"中止: Mail に作成中のメッセージが {n} 件開いています。\n"
            "  reply/forward は開いている別の作成中メッセージを掴むことがあり、\n"
            "  まったく別のスレッドへ返信が作られます（2026-08-25 に実害あり）。\n"
            "  → すべて閉じてから再実行してください。\n"
            "  （意図して残したまま実行するなら --allow-open-drafts）"
        )


SUBJECT_SEP = "@@AMD-SUBJECT-SPLIT@@"  # 件名と本文の区切り（件名に現れない文字列）

# 返信・転送で件名の頭に付く接頭辞（小文字で比較する）。
_RE_PREFIXES = ("re:", "re :", "返信:", "fwd:", "fw:", "fwd :", "fw :", "転送:")


def _strip_re(subject: str) -> str:
    s = subject.strip()
    changed = True
    while changed:
        changed = False
        for pre in _RE_PREFIXES:
            if s.lower().startswith(pre):
                s = s[len(pre):].strip()
                changed = True
    return s


def verify_draft_subject(orig_subject: str, draft_subject: str) -> bool:
    """作られた下書きが本当に元メールへの返信／転送かを件名で照合する。

    誤爆すると「元メールとは無関係な件名」の下書きに本文が入る。Re: / Fwd: の
    付き方はロケール・元件名の接頭辞の有無で揺れるので、接頭辞を剥がした芯で比べる。

    draft_subject には --subject で上書きする**前**の件名を渡すこと。上書き後を
    渡すと、別ウィンドウを掴んでいてもその件名が指定値へ変わるだけなので、照合が
    素通りするか、正しい下書きを誤検知するかのどちらかになる。
    """
    return _strip_re(orig_subject) == _strip_re(draft_subject)


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
    # --no-quote は reply/reply-all 専用。転送で引用を消すと転送の意味が無くなるので、
    # forward では受け取っても main() で明示的にエラーにする。
    sp.add_argument("--no-quote", action="store_true",
                    help="元メールの引用文を残さず本文だけに置き換える(reply のみ)")
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
    sp_reply.add_argument(
        "--allow-open-drafts", action="store_true",
        help="作成中ウィンドウが開いていても実行する（⚠️ 誤爆の危険。既定は中止）",
    )

    sp_fwd = sub.add_parser("forward", help="転送の下書き(--to で転送先)")
    add_target(sp_fwd)
    add_common(sp_fwd, need_subject=False)
    sp_fwd.add_argument("--from", dest="sender", help=argparse.SUPPRESS)
    sp_fwd.add_argument(
        "--allow-open-drafts", action="store_true",
        help="作成中ウィンドウが開いていても実行する（⚠️ 誤爆の危険。既定は中止）",
    )

    args = p.parse_args()
    if not hasattr(args, "allow_open_drafts"):
        args.allow_open_drafts = False
    resolve_body(args)

    if args.mode == "new":
        if not args.to:
            p.error("new には --to が必要です")
        script = build_new(args)
    elif args.mode in ("reply", "forward"):
        if args.mode == "forward":
            if not args.to:
                p.error("forward には --to(転送先)が必要です")
            if args.no_quote:
                p.error("forward では --no-quote は使えません"
                        "（転送は元メールの引用が本体のため）")
        if not args.dry_run and not args.allow_open_drafts:
            assert_no_open_drafts()
        script = build_reply(args, args.all) if args.mode == "reply" else build_forward(args)
    else:  # pragma: no cover
        p.error(f"unknown mode: {args.mode}")

    if args.dry_run:
        print(script)
        return 0

    try:
        out = run_applescript(script)
    except RuntimeError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1

    if SUBJECT_SEP in out:
        orig_subject, native_subject, out = out.split(SUBJECT_SEP, 2)
        print(out)
        # 誤爆の検知は「作られた下書きの件名が元メールのものか」で行う。比べるのは
        # --subject で上書きする前の件名（nativeSubject）。save 済みなので下書きは
        # 残る。貼り付けさせないことが最優先。
        if not verify_draft_subject(orig_subject, native_subject):
            kind = "返信" if args.mode == "reply" else "転送"
            print(
                "\n"
                f"🚨 中止してください: 作られた下書きが元メールの{kind}になっていません。\n"
                f"  元メールの件名 : {orig_subject}\n"
                f"  下書きの件名   : {native_subject}\n"
                "  別の作成中メッセージを掴んだ可能性があります（2026-08-25 の誤爆と同じ症状）。\n"
                "  ⚠️ 貼り付け（⌘V）も送信もせず、開いている下書きを確認して破棄してください。",
                file=sys.stderr,
            )
            return 2
        return 0

    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
