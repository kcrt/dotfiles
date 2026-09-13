#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Exercise every module in script/lib, as a demo and as a self-check.

Run it after touching anything under lib/: each section prints what the module
produces (so the alignment, the colors and the animation can be eyeballed) and
asserts the cases that have a single right answer.

    ./sample.py                       every section
    ./sample.py termtext humanize     only these
    ./sample.py --color never         force the no-color path
    ./sample.py --seconds 8           run the progress demo longer
    ./sample.py --interactive         also ask a real question (prompt_choice)
    ./sample.py --trash               really move a temporary file to the Trash

Exit code is 1 if any check failed, so it can be used in a pre-commit hook.
"""

from __future__ import annotations

import argparse
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
from collections.abc import Callable
from contextlib import redirect_stdout
from pathlib import Path

# lib/* import each other relatively (`from .termtext import ...`), which needs the
# package rather than the directory. Running this file directly puts lib/ itself at
# sys.path[0], so add its parent to make `lib` importable under its own name.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.humanize import clock, common_unit, human, size_change, size_unit
from lib.progressbar import (BarSlot, LiveLine, bar_chars, rainbow_rgb,
                             render_bar, wave_level)
from lib.ffprobe import ProbeError, probe_chapters, probe_json
from lib.prompt import confirm, interactive, prompt_choice
from lib.termcolor import (BRIGHT_RED, GREEN, RED, bold, color_enabled, hue_rgb,
                           paint, paint16, paint256, scale_rgb, set_color_mode,
                           status_line, use_color)
from lib.termtext import (clip_display, display_width, fit_display, pad_display,
                          strip_sgr, truncate_display)
from lib.trash import move_to_trash, trash_directory

# Mixed-width sample in the NFD form macOS filenames arrive in: ASCII, full-width
# Japanese, and a voiced kana written as its base plus a combining dakuten. All three
# have to be measured correctly, and len() is visibly wrong for everything but ASCII.
SAMPLE_TEXT = unicodedata.normalize("NFD", "映像 video ガイド.mp4")
NFD_GA = unicodedata.normalize("NFD", "が")

OK_RGB, NG_RGB = (60, 190, 110), (225, 70, 70)

_failures = 0


def heading(title: str) -> None:
    print(f"\n\033[1m== {title} ==\033[0m" if use_color() else f"\n== {title} ==")


def check(label: str, actual: object, expected: object) -> None:
    """Assert one value without stopping the run, so every section still gets shown."""
    global _failures
    passed = actual == expected
    if not passed:
        _failures += 1
    mark = paint("ok", OK_RGB) if passed else paint("NG", NG_RGB)
    detail = "" if passed else f"   got {actual!r}, want {expected!r}"
    print(f"  {mark}  {label}{detail}")


# -- sections ---------------------------------------------------------------


def demo_termtext(opts: argparse.Namespace) -> None:
    heading("termtext — display width, padding, truncation")
    print(f"  text: {SAMPLE_TEXT!r}")
    print(f"  display_width: {display_width(SAMPLE_TEXT)} (len: {len(SAMPLE_TEXT)})")

    # A ruler above the columns: if the width arithmetic is wrong, the right edge
    # of the box drifts away from the ruler's tick.
    width = 14
    print(f"\n  fit_display(width={width}), aligned against the ruler:")
    print("  " + "".join(str(i % 10) for i in range(1, width + 1)) + "|")
    for text in (SAMPLE_TEXT, "short", "日本語のファイル名.mp4", NFD_GA * 4):
        print(f"  {fit_display(text, width)}|  <- {text!r}")
    print(f"  {fit_display('right', width, align='>')}|  <- align='>'")

    print("\n  truncate_display keeps the ellipsis inside the limit:")
    for limit in (20, 10, 4):
        cut = truncate_display(SAMPLE_TEXT, limit)
        print(f"    limit {limit:2d}: {cut!r} (width {display_width(cut)})")

    colored = paint("colored", OK_RGB)
    check("display_width ignores SGR", display_width(colored), len("colored"))
    check("strip_sgr removes SGR", strip_sgr(colored), "colored")
    check("full-width counts as 2", display_width("映像"), 4)
    check("combining mark counts as 0", display_width(NFD_GA), 2)
    check("pad_display pads to width", display_width(pad_display("映像", 10)), 10)
    check("pad_display never shrinks", pad_display("映像", 2), "映像")
    check("clip_display stops before a full-width char", clip_display("映像", 3), ("映", 2))
    check("fit_display is exactly width", display_width(fit_display(SAMPLE_TEXT, 9)), 9)
    check("truncate_display stays within limit",
          display_width(truncate_display(SAMPLE_TEXT, 8)) <= 8, True)


def demo_termcolor(opts: argparse.Namespace) -> None:
    heading("termcolor — color detection and painting")
    print(f"  color_enabled (256): {color_enabled()}")
    print(f"  use_color (24bit):   {use_color()}")
    environment = "  ".join(f"{name}={os.environ.get(name, '')!r}"
                            for name in ("COLORTERM", "TERM", "NO_COLOR"))
    print(f"  {environment}  isatty={sys.stdout.isatty()}")

    print("\n  hue_rgb around the wheel:")
    print("  " + "".join(paint("██", hue_rgb(i / 24)) for i in range(24)))
    print("\n  scale_rgb, dark to bright:")
    print("  " + "".join(paint("██", scale_rgb((70, 145, 240), level / 10))
                         for level in range(2, 12)))
    print("\n  the basic 16 (these follow the terminal theme, unlike the two above):")
    print("  normal " + " ".join(paint16("██", code) for code in range(30, 38)))
    print("  bright " + " ".join(paint16("██", code) for code in range(90, 98)))
    print("  " + bold("bold") + " is not a color, so it composes with one: "
          + bold(paint16("bold red", RED)))

    print("\n  paint256 over the 6x6x6 cube:")
    print("  " + "".join(paint256("█", 16 + i * 5) for i in range(43)))

    print("\n  status_line keeps the text column aligned whether or not the marker is colored:")
    for marker, rgb, text in (("ok", OK_RGB, "映像.mp4: 変換しました"),
                              ("NG", NG_RGB, "音声.wav: 読めません"),
                              ("skip", None, "already converted")):
        print(status_line(marker, rgb, text))

    plain_width = display_width(status_line("NG", None, "x"))
    check("status_line width is color-independent",
          display_width(status_line("NG", NG_RGB, "x")), plain_width)
    check("paint16 spells the expected SGR", paint16("x", GREEN),
          "\033[32mx\033[0m" if color_enabled() else "x")
    check("bright is the base color plus 60", BRIGHT_RED - RED, 60)
    check("hue_rgb wraps around 1.0", hue_rgb(1.25), hue_rgb(0.25))
    check("scale_rgb clamps at 255", scale_rgb((200, 200, 200), 4.0), (255, 255, 255))
    try:
        set_color_mode("rainbow")
    except ValueError:
        check("set_color_mode rejects an unknown mode", True, True)
    else:
        check("set_color_mode rejects an unknown mode", False, True)
    set_color_mode(opts.color)   # restore what the command line asked for


def demo_humanize(opts: argparse.Namespace) -> None:
    heading("humanize — byte counts and durations")
    print("  human() on its own:")
    for n in (0, 512, 1536, 1024 ** 2 * 1.5, 1024 ** 3 * 2.25, 1024 ** 4 * 3):
        print(f"    {human(n):>12}   sep='': {human(n, sep=''):>10}   "
              f"align: |{human(n, align=True)}|")

    print("\n  size_change() lines up as a column, and marks a file that grew:")
    pairs = ((1024 ** 2 * 1.3, 1024 * 800), (1024 ** 3, 1024 ** 2 * 194),
             (1024 ** 2 * 5, 1024 ** 2 * 7), (1024 * 900, 1024 * 890))
    for src, dst in pairs:
        print(f"    {size_change(int(src), int(dst))}")
    print("  with show_saved=True (the total line):")
    for src, dst in pairs[:1] + pairs[2:3]:
        print(f"    {size_change(int(src), int(dst), show_saved=True)}")

    print("\n  clock():", ", ".join(clock(s) for s in (0, 9, 62, 3723, 86399)))
    print("  clock(always_hours=True):",
          ", ".join(clock(s, always_hours=True) for s in (0, 9, 62, 3723, 86399)))

    check("size_unit picks KB", size_unit(2048), "KB")
    check("common_unit follows the larger side", common_unit(1024 ** 2, 1024), "MB")
    check("human keeps 2 decimals below 1", human(1024 ** 2 * 0.5, "MB"), "0.50 MB")
    check("human honors sep", human(1024 * 1536, sep=""), "1.5MB")
    check("align keeps a fixed width",
          len(strip_sgr(human(1024, align=True))), len(strip_sgr(human(1024 ** 4, align=True))))
    check("clock under an hour", clock(62), "1:02")
    check("clock over an hour", clock(3723), "1:02:03")
    check("clock clamps negatives", clock(-5), "0:00")
    check("always_hours pads the hour field", clock(62, always_hours=True), "00:01:02")
    check("always_hours keeps the column width",
          len(clock(9, always_hours=True)), len(clock(3723, always_hours=True)))
    check("size_change handles a zero source", "0%" in size_change(0, 0), True)


def demo_progressbar(opts: argparse.Namespace) -> None:
    heading("progressbar — bar rendering and the live line")
    print("  render_bar at a few ratios (partial blocks fill the remainder):")
    for ratio in (0.0, 0.07, 0.333, 0.5, 0.875, 1.0):
        print(f"    {ratio:6.1%} {render_bar(ratio, 24)}")
    if use_color():
        print("\n  colored, single color with a sheen, and rainbow (phase fixed):")
        print("    " + render_bar(0.66, 24,
                                  lambda p: scale_rgb((70, 145, 240), wave_level(p, 0.0))))
        print("    " + render_bar(0.66, 24, lambda p: rainbow_rgb(p, 0.0)))
    else:
        # render_bar colors whatever it is given; keeping the escapes out of a pipe
        # is the caller's job, exactly as LiveLine does it through self.color.
        print("\n  (24bit color is off, so the colored bars are skipped)")

    check("bar_chars length is the width", len(bar_chars(0.5, 20)), 20)
    check("ratio 0 leaves the bar empty", set(bar_chars(0.0, 10)), {"░"})
    check("ratio 1 fills the bar", set(bar_chars(1.0, 10)), {"█"})
    check("a negative ratio is clamped", set(bar_chars(-1.0, 10)), {"░"})
    check("render_bar has the frame", render_bar(0.0, 4), "[░░░░]")
    check("a partial block appears mid-cell", bar_chars(0.25, 2)[0], "▌")

    enabled = sys.stdout.isatty()
    print(f"\n  LiveLine demo ({opts.seconds:g}s, enabled={enabled}). "
          f"{'Watch the last line.' if enabled else 'Not a terminal: nothing is drawn.'}")
    run_live_line(opts.seconds, rainbow=opts.rainbow)


class DemoProgress(LiveLine):
    """A LiveLine whose fields appear and disappear, to show the width holding steady."""

    def __init__(self, total: int, rainbow: bool = False, **kwargs: object) -> None:
        super().__init__(**kwargs)   # type: ignore[arg-type]
        self.total = total
        self.done = 0
        self.name = ""
        self.rainbow = rainbow

    @property
    def ratio(self) -> float:
        return self.done / self.total

    def parts(self) -> list[str | BarSlot]:
        elapsed = time.monotonic() - self.started
        fields: list[str | BarSlot] = [
            f"{self.done:3d}/{self.total}",
            BarSlot(self.ratio, intensity=self.ratio),
            f"{self.ratio:4.0%}",
            clock(elapsed),
        ]
        if self.name:   # only present while a job is running
            fields.append(fit_display(self.name, 18))
        return fields

    def cell_color(self, slot: BarSlot, position: float, phase: float):
        if self.rainbow:
            return rainbow_rgb(position, phase)
        return super().cell_color(slot, position, phase)


def run_live_line(seconds: float, rainbow: bool = False) -> None:
    """Drive a DemoProgress for `seconds`, printing a couple of result lines on the way."""
    total = 24
    with DemoProgress(total, rainbow=rainbow, enabled=sys.stdout.isatty()) as progress:
        for step in range(total):
            time.sleep(seconds / total)
            with progress.lock:
                progress.done = step + 1
                # Blank the name every few steps: the bar must not jump when it returns
                progress.name = f"映像 {step + 1:02d}.mp4" if step % 6 < 4 else ""
            progress.refresh()
            if step in (total // 3, total - 1):
                progress.report(status_line("ok", OK_RGB,
                                            f"映像 {step + 1:02d}.mp4: "
                                            f"{size_change(1024 ** 2 * 13, 1024 ** 2 * 4)}"))
    print("  done (the progress line erased itself)")


def answer(feed: str, default: bool) -> bool:
    """Run confirm() against a canned answer, with its prompt swallowed.

    Lets the yes/no parsing be checked without a terminal: `feed` is what the
    person would have typed, and "" stands for EOF (a pipe that ran dry).
    """
    saved = sys.stdin
    sys.stdin = io.StringIO(feed)
    try:
        with redirect_stdout(io.StringIO()):
            return confirm("Q", default)
    finally:
        sys.stdin = saved


def demo_prompt(opts: argparse.Namespace) -> None:
    heading("prompt — interactivity check, yes/no, and the choice prompt")
    print(f"  interactive(): {interactive()}  "
          f"(stdin tty: {sys.stdin.isatty()}, stdout tty: {sys.stdout.isatty()})")

    print("\n  confirm() writes the hint itself, so every script asks the same shape:")
    print("    Overwrite the file? [y/N]:      <- confirm(question)")
    print("    Keep the new file? [Y/n]:       <- confirm(question, default=True)")
    check("empty input takes the default (yes)", answer("\n", True), True)
    check("empty input takes the default (no)", answer("\n", False), False)
    check("EOF takes the default", answer("", True), True)
    check("yes is accepted spelled out", answer("YES\n", False), True)
    check("no wins over a yes default", answer("n\n", True), False)
    check("a typo asks again instead of counting as no", answer("maybe\ny\n", False), True)

    options = [("hevc", "HEVC (H.265)"), ("h264", "H.264"), ("av1", "AV1")]
    if not opts.interactive:
        print("  skipping the real prompt; pass --interactive to answer it. It looks like:")
        print("\n    どのコーデックにしますか？")
        for number, (value, label) in enumerate(options, start=1):
            print(f"      {number}) {label}{' ← 既定' if value == 'hevc' else ''}")
        print("    番号 (Enterで既定): ")
        return
    if not interactive():
        print("  --interactive was passed but there is no terminal on both ends; skipping.")
        return
    chosen = prompt_choice("どのコーデックにしますか？", options, "hevc")
    print(f"  chose: {chosen!r}")
    print(f"  confirm: {confirm('Was that the one you wanted?', default=True)}")


def demo_ffprobe(opts: argparse.Namespace) -> None:
    heading("ffprobe — chapters and container metadata")
    if shutil.which("ffprobe") is None or shutil.which("ffmpeg") is None:
        print("  ffmpeg/ffprobe not installed; skipping (brew install ffmpeg).")
        return

    with tempfile.TemporaryDirectory() as workdir:
        # The name carries a space, a quote and a $ on purpose: interpolated into a
        # shell string this file would be unreachable, which is what the argument
        # list inside probe_json() avoids.
        path = Path(workdir) / 'chapter test "$x".m4a'
        make_sample_media(path)
        result = probe_chapters(path)
        print(f"  file:   {path.name}")
        print(f"  format: {clock(result.format.duration)}, "
              f"{human(result.format.bit_rate / 8)}/s, "
              f"album={result.format.tags.get('album')!r}")
        for chapter in result.chapters:
            print(f"    chapter {chapter.id}: "
                  f"{clock(chapter.start_time)}-{clock(chapter.end_time)} {chapter.title!r}")
        streams = probe_json(path, "-show_streams")["streams"]
        print(f"  probe_json: {len(streams)} stream(s), first is {streams[0]['codec_name']}")

        check("the awkward filename was probed anyway", len(result.chapters), 2)
        check("chapter bounds are seconds", result.chapters[0].end_time, 3.0)
        check("the title comes through the tags", result.chapters[1].title, "第2章")
        check("duration is a float", round(result.format.duration), 6)

    try:
        probe_chapters("/etc/hosts")
    except ProbeError as error:
        check("a non-media file raises ProbeError", "Invalid data" in str(error), True)
    else:
        check("a non-media file raises ProbeError", False, True)
    try:
        probe_chapters(Path(tempfile.gettempdir()) / "no such file.m4a")
    except ProbeError:
        check("a missing file raises ProbeError", True, True)
    else:
        check("a missing file raises ProbeError", False, True)


def make_sample_media(path: Path) -> None:
    """Write a 6-second tone with two named chapters, for the ffprobe section."""
    metadata = path.with_suffix(".txt")
    metadata.write_text(
        ";FFMETADATA1\nalbum=テストアルバム\nartist=kcrt\n\n"
        "[CHAPTER]\nTIMEBASE=1/1000\nSTART=0\nEND=3000\ntitle=第1章\n\n"
        "[CHAPTER]\nTIMEBASE=1/1000\nSTART=3000\nEND=6000\ntitle=第2章\n",
        encoding="utf-8")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "sine=frequency=440:duration=6",
         "-i", str(metadata), "-map_metadata", "1", str(path)],
        check=True, capture_output=True)


def demo_trash(opts: argparse.Namespace) -> None:
    heading("trash — where a file would go, and optionally a real round trip")
    here = Path.cwd()
    destination = trash_directory(here)
    print(f"  cwd:   {here}")
    print(f"  trash: {destination}")
    check("the trash directory exists", destination.is_dir(), True)

    if not opts.trash:
        print("  not moving anything; pass --trash for a real round trip.")
        return
    victim = here / f"sample.py trash test {time.strftime('%Y-%m-%d-%H-%M-%S')}.txt"
    victim.write_text("script/lib/sample.py test file\n", encoding="utf-8")
    print(f"  created: {victim.name}")
    move_to_trash(victim)
    moved = destination / victim.name
    check("the file left the working directory", victim.exists(), False)
    check("the file arrived in the trash", moved.is_file(), True)
    if moved.is_file():
        moved.unlink()   # clean up after ourselves rather than leaving litter behind
        print("  removed the test file from the trash again")


SECTIONS: dict[str, Callable[[argparse.Namespace], None]] = {
    "termtext": demo_termtext,
    "termcolor": demo_termcolor,
    "humanize": demo_humanize,
    "progressbar": demo_progressbar,
    "prompt": demo_prompt,
    "ffprobe": demo_ffprobe,
    "trash": demo_trash,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Demo and self-check for the modules in script/lib.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="sections: " + ", ".join(SECTIONS))
    parser.add_argument("sections", nargs="*", choices=[*SECTIONS, []],
                        help="sections to run (default: all)")
    parser.add_argument("--color", choices=("auto", "always", "never"), default="auto",
                        help="force color on or off (default: auto)")
    parser.add_argument("--seconds", type=float, default=3.0,
                        help="how long the LiveLine demo runs (default: 3)")
    parser.add_argument("--rainbow", action="store_true",
                        help="use the rainbow bar in the LiveLine demo")
    parser.add_argument("--interactive", action="store_true",
                        help="actually ask the prompt_choice question")
    parser.add_argument("--trash", action="store_true",
                        help="really move a temporary file to the Trash and back out")
    return parser.parse_args()


def main() -> int:
    opts = parse_args()
    set_color_mode(opts.color)
    for name in opts.sections or SECTIONS:
        SECTIONS[name](opts)
    heading("result")
    if _failures:
        print(paint(f"  {_failures} check(s) failed", NG_RGB))
        return 1
    print(paint("  all checks passed", OK_RGB))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
