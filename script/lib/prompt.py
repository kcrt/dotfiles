# -*- coding: utf-8 -*-
"""Small interactive prompts for the terminal.

Asking only makes sense when a person ran the script from a terminal, so the
interactive() check lives here too. Under a pipe, under cron, or with
--no-interactive, the caller falls back to its defaults instead of asking.

Every question here treats EOF as "take the default" and Ctrl-C as an interrupt,
so a script never dies with a traceback when its input runs out.

Use the standard library only (see termtext for why).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

# Exit code for an interrupt with Ctrl-C (128 + SIGINT).
INTERRUPTED_EXIT_CODE = 130

# What counts as yes and no, whatever the caller's question was worded like.
YES_ANSWERS = ("y", "yes")
NO_ANSWERS = ("n", "no")

# Shown on stderr when Ctrl-C interrupts a prompt that has wording of its own.
INTERRUPTED_MESSAGE = "中断しました"


@dataclass(frozen=True)
class ChoiceWords:
    """The wording around prompt_choice(), so a script can pick its language.

    confirm() and prompt_text() get away with "[y/N]" and "[default]", but a
    numbered menu has to say things out loud, and which language it says them in
    is the caller's business, not this module's.
    """

    default_mark: str
    ask: str
    retry: str


JAPANESE_CHOICE = ChoiceWords(
    default_mark=" ← 既定",
    ask="番号 (Enterで既定): ",
    retry="1〜{count} の番号で答えてください")

ENGLISH_CHOICE = ChoiceWords(
    default_mark=" <- default",
    ask="Number (Enter for the default): ",
    retry="answer with a number from 1 to {count}")


def interactive() -> bool:
    """Whether a person is sitting at a terminal. False under a pipe or cron.

    Both input and output are checked: with output on a terminal but input from a
    pipe, there is no way to answer the question.
    """
    return sys.stdin.isatty() and sys.stdout.isatty()


def _ask(question: str, interrupted_message: str = "", fold_case: bool = True) -> str | None:
    """Read one answer, stripped and by default lowercased. None means EOF.

    The caller turns None into its own default. Ctrl-C ends the run with
    INTERRUPTED_EXIT_CODE instead of raising through the caller, so every prompt
    in every script quits the same way.
    """
    try:
        answer = input(question).strip()
        return answer.lower() if fold_case else answer
    except EOFError:
        print()
        return None
    except KeyboardInterrupt:
        print("\n" + interrupted_message, file=sys.stderr)
        raise SystemExit(INTERRUPTED_EXIT_CODE)


def confirm(question: str, default: bool = False) -> bool:
    """Ask a yes/no question. Empty input and EOF take `default`.

    The "[y/N]" hint is added here from `default`, so callers pass the question
    alone and every script shows the same shape. Anything but yes/no is asked
    again rather than silently counted as no: a typo should not delete files.
    """
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        answer = _ask(f"{question} {hint}: ")
        if answer is None or not answer:
            return default
        if answer in YES_ANSWERS:
            return True
        if answer in NO_ANSWERS:
            return False
        print("  y / n")


def prompt_text(question: str, default: str = "") -> str:
    """Ask for a line of text. Empty input and EOF take `default`.

    Case is left alone, unlike the yes/no answers: this is for the things a
    person types out, such as a path or a title, where folding it would be wrong.
    The "[default]" hint is added here so every script shows the same shape.
    """
    hint = f" [{default}]" if default else ""
    answer = _ask(f"{question}{hint}: ", INTERRUPTED_MESSAGE, fold_case=False)
    return default if answer is None or not answer else answer


def prompt_choice(question: str, options: list[tuple[str, str]], default: str,
                  words: ChoiceWords = JAPANESE_CHOICE) -> str:
    """Pick one option by number. `options` is a sequence of (value, label).

    Empty input and EOF take the default. Ctrl-C is treated as an interrupt.
    Pass ENGLISH_CHOICE from a script that speaks English throughout.
    """
    print(f"\n{question}")
    for number, (value, label) in enumerate(options, start=1):
        print(f"  {number}) {label}{words.default_mark if value == default else ''}")
    while True:
        answer = _ask(words.ask, INTERRUPTED_MESSAGE)
        if answer is None or not answer:
            return default
        try:
            chosen = int(answer)
        except ValueError:
            chosen = 0
        if 1 <= chosen <= len(options):
            return options[chosen - 1][0]
        print("  " + words.retry.format(count=len(options)))
