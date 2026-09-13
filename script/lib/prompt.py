# -*- coding: utf-8 -*-
"""端末での簡単な対話。

聞くのは端末から人が実行したときだけにしたいので、判定用の interactive() も
ここに置く。パイプ・cron・--no-interactive では呼ぶ側が既定値へ落とす。

標準ライブラリだけで書くこと（理由は termtext を参照）。
"""

from __future__ import annotations

import sys

# Ctrl-C で中断したときの終了コード（128 + SIGINT）。
INTERRUPTED_EXIT_CODE = 130


def interactive() -> bool:
    """人が端末の前にいるか。パイプ・cron では False。

    入力と出力の両方を見る。出力だけ端末でも、入力がパイプなら質問に答えられない。
    """
    return sys.stdin.isatty() and sys.stdout.isatty()


def prompt_choice(question: str, options: list[tuple[str, str]], default: str) -> str:
    """番号でひとつ選ばせる。options は (値, 説明) の並び。

    空入力とEOFは既定値。Ctrl-Cは中断として扱う。
    """
    print(f"\n{question}")
    for number, (value, label) in enumerate(options, start=1):
        print(f"  {number}) {label}{' ← 既定' if value == default else ''}")
    while True:
        try:
            answer = input("番号 (Enterで既定): ").strip()
        except EOFError:
            print()
            return default
        except KeyboardInterrupt:
            print("\n中断しました", file=sys.stderr)
            raise SystemExit(INTERRUPTED_EXIT_CODE)
        if not answer:
            return default
        try:
            chosen = int(answer)
        except ValueError:
            chosen = 0
        if 1 <= chosen <= len(options):
            return options[chosen - 1][0]
        print(f"  1〜{len(options)} の番号で答えてください")
