# -*- coding: utf-8 -*-
"""Small interactive prompts for the terminal.

Asking only makes sense when a person ran the script from a terminal, so the
interactive() check lives here too. Under a pipe, under cron, or with
--no-interactive, the caller falls back to its defaults instead of asking.

Use the standard library only (see termtext for why).
"""

from __future__ import annotations

import sys

# Exit code for an interrupt with Ctrl-C (128 + SIGINT).
INTERRUPTED_EXIT_CODE = 130


def interactive() -> bool:
    """Whether a person is sitting at a terminal. False under a pipe or cron.

    Both input and output are checked: with output on a terminal but input from a
    pipe, there is no way to answer the question.
    """
    return sys.stdin.isatty() and sys.stdout.isatty()


def prompt_choice(question: str, options: list[tuple[str, str]], default: str) -> str:
    """Pick one option by number. `options` is a sequence of (value, label).

    Empty input and EOF take the default. Ctrl-C is treated as an interrupt.
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
