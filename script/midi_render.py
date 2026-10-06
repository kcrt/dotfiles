#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
"""MIDI (SMF) を SoundFont で鳴らして m4a / flac / wav にする（--play なら再生だけ）。

FluidSynth で 32bit float の WAV に書き出し、ピークを -1 dBFS に揃えてから
ffmpeg でエンコードする（m4a は AudioToolbox の AAC 256 kbps）。タグは
曲名 = ファイル名、コメント = 使った SoundFont の名前。

例:
  midi_render.py -s GeneralUser-GS.sf2 song.mid            同じ場所に song.m4a
  midi_render.py -s GeneralUser-GS.sf2 song.mid -o out.flac
  midi_render.py -s GeneralUser-GS.sf2 midi/ -o rendered/  ディレクトリ内の .mid をまとめて
  SOUNDFONT=~/sf2/SGM-V2b.sf2 midi_render.py *.mid -f wav  SoundFont は環境変数でも指定できる
  midi_render.py -s GeneralUser-GS.sf2 --play midi/        書き出さずにその場で順に再生（Ctrl-C で止める）

必要なもの: brew install ffmpeg fluid-synth、GM/GS の SoundFont（.sf2 / .sf3）
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Final

MIDI_SUFFIXES: Final = frozenset({".mid", ".midi", ".smf"})
FORMAT_CODECS: Final[dict[str, list[str]]] = {
    "m4a": ["-c:a", "aac_at", "-b:a", "256k"],
    "flac": ["-c:a", "flac"],
    "wav": ["-c:a", "pcm_s16le"],
}


def collect_midi_files(inputs: list[Path]) -> list[Path]:
    """入力のファイルと、ディレクトリ直下の MIDI ファイルを並べる。"""
    files: list[Path] = []
    for path in inputs:
        if path.is_dir():
            files += sorted(p for p in path.iterdir() if p.suffix.lower() in MIDI_SUFFIXES)
        elif path.is_file():
            files.append(path)
        else:
            raise SystemExit(f"{path}: 見つかりません")
    if not files:
        raise SystemExit("MIDI ファイルがありません")
    return files


def render_wav(midi: Path, soundfont: Path, wav: Path, sample_rate: int) -> None:
    subprocess.run(
        ["fluidsynth", "-ni", "-q", "-O", "float", "-r", str(sample_rate), "-F", str(wav),
         str(soundfont), str(midi)],
        check=True, capture_output=True,
    )


def play(midi_files: list[Path], soundfont: Path, gain: float | None) -> None:
    """既定のオーディオ出力で順に鳴らす。音量は揃えない（FluidSynth の -g で調整）。"""
    command = ["fluidsynth", "-ni", "-q"]
    if gain is not None:
        command += ["-g", str(gain)]
    for midi in midi_files:
        print(f"♪ {midi.name}", file=sys.stderr)
    try:
        subprocess.run([*command, str(soundfont), *map(str, midi_files)], check=True)
    except KeyboardInterrupt:
        raise SystemExit(130) from None


def peak_dbfs(path: Path) -> float:
    """float のままピークを測る（volumedetect は 16bit に丸めるので 0 dBFS 超えが 0.0 dB に張り付く）。"""
    result = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(path),
         "-af", "astats=measure_perchannel=none:measure_overall=Peak_level", "-f", "null", "-"],
        check=True, capture_output=True, text=True,
    )
    match = re.search(r"Peak level dB: (-?[\d.]+)", result.stderr)
    if match is None:
        raise SystemExit(f"{path}: ピークを測れませんでした（無音?）")
    return float(match[1])


def encode(wav: Path, target: Path, audio_format: str, sample_rate: int, gain_db: float,
           tags: dict[str, str]) -> None:
    command = ["ffmpeg", "-v", "error", "-y", "-i", str(wav)]
    if gain_db:
        command += ["-af", f"volume={gain_db:.2f}dB"]
    command += ["-ar", str(sample_rate), *FORMAT_CODECS[audio_format]]
    for key, value in tags.items():
        command += ["-metadata", f"{key}={value}"]
    subprocess.run([*command, str(target)], check=True)


def output_path(midi: Path, output: Path | None, audio_format: str, single_file: bool) -> Path:
    """-o が無ければ MIDI の隣、ファイル名なら（入力が1つのとき）そのまま、それ以外はディレクトリとして扱う。"""
    if output is None:
        return midi.with_suffix(f".{audio_format}")
    if single_file and output.suffix.lower().lstrip(".") in FORMAT_CODECS:
        return output
    return output / f"{midi.stem}.{audio_format}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inputs", type=Path, nargs="+", help="MIDI ファイル、または MIDI を含むディレクトリ")
    parser.add_argument("-s", "--soundfont", type=Path, default=os.environ.get("SOUNDFONT"),
                        help="SoundFont (.sf2 / .sf3)。省略時は環境変数 SOUNDFONT")
    parser.add_argument("-o", "--output", type=Path,
                        help="出力ファイル（入力が1つのとき）またはディレクトリ。省略時は MIDI と同じ場所")
    parser.add_argument("-f", "--format", choices=sorted(FORMAT_CODECS),
                        help="出力形式（既定 m4a。-o のファイル名に拡張子があればそれに従う）")
    parser.add_argument("-r", "--sample-rate", type=int, default=44100)
    parser.add_argument("--peak", type=float, default=-1.0, help="ピークを揃える先の dBFS（既定 -1.0）")
    parser.add_argument("--no-normalize", action="store_true", help="音量を揃えない（FluidSynth の出力のまま）")
    parser.add_argument("--overwrite", action="store_true", help="既存の出力を上書きする")
    parser.add_argument("--play", action="store_true", help="書き出さずに再生する（-o / -f などは使わない）")
    parser.add_argument("--gain", type=float, help="--play の音量（FluidSynth の -g、既定 0.2）")
    args = parser.parse_args()

    if args.play and (args.output or args.format):
        parser.error("--play と -o / -f は同時に使えません")
    for tool in ("fluidsynth",) if args.play else ("ffmpeg", "fluidsynth"):
        if shutil.which(tool) is None:
            parser.error(f"{tool} が見つかりません（brew install ffmpeg fluid-synth）")
    if args.soundfont is None:
        parser.error("SoundFont を -s か環境変数 SOUNDFONT で指定してください")
    soundfont = args.soundfont.expanduser()
    if not soundfont.is_file():
        parser.error(f"{soundfont}: SoundFont が見つかりません")

    midi_files = collect_midi_files(args.inputs)
    if args.play:
        play(midi_files, soundfont, args.gain)
        return
    single_file = len(midi_files) == 1
    output_suffix = args.output.suffix.lower().lstrip(".") if args.output else ""
    audio_format = args.format or (output_suffix if single_file and output_suffix in FORMAT_CODECS else "m4a")
    comment = f"FluidSynth, {soundfont.name}"

    with tempfile.TemporaryDirectory() as work:
        for midi in midi_files:
            target = output_path(midi, args.output, audio_format, single_file)
            if target.exists() and not args.overwrite:
                print(f"skip (exists): {target}", file=sys.stderr)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            wav = Path(work, f"{midi.stem}.wav")
            render_wav(midi, soundfont, wav, args.sample_rate)
            gain = 0.0 if args.no_normalize else args.peak - peak_dbfs(wav)
            encode(wav, target, audio_format, args.sample_rate, gain, {"title": midi.stem, "comment": comment})
            wav.unlink()
            print(f"{midi.name}\t→ {target}\tgain {gain:+.1f} dB")


if __name__ == "__main__":
    main()
