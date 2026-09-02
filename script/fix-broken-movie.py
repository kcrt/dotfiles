#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""libavcodecが復号できない音声トラックを、Appleのデコーダ経由で作り直す。

配信サイトから取得した動画などで、AACの中身が壊れていることがある。厄介なのは
壊れ方がデコーダによって表に出たり出なかったりすることで、次のように分かれる:

  Apple (AudioToolbox / AVFoundation) … 最後まで正常に再生できる
      → QuickTime、QuickLook、写真.app、Safari
  libavcodec … 途中から完全な無音、あるいはノイズになる
      → ffmpeg、mpv、VLC、IINA、Chrome、Firefox

libavcodec側は復号を続けながら内部状態を壊していくため、先頭は正常でも途中から
出力が止まる。シークすると復帰するので、データ自体は全編に存在している。

そこで afconvert（＝Appleのデコーダ）で読み直してAACに入れ直す。映像には触らない。
AAC→AACの再エンコードなので世代劣化が1回乗るが、元が壊れている以上ほかに手がない。

    fix-broken-movie.py *.mp4 --check      # 調べるだけ
    fix-broken-movie.py *.mp4 -o fixed     # 壊れているものだけ直す

macOS専用（afconvertを使うため）。元ファイルは変更しない。
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

VIDEO_SUFFIXES = frozenset({".mp4", ".mov", ".m4v", ".mkv", ".avi", ".ts", ".webm", ".flv"})

# libavcodecのAACデコーダが「読めていない」ことを示す警告。
# 正常なファイルではひとつも出ない。
DECODER_COMPLAINTS = (
    "SBR reset failed",
    "ChannelElement",
    "Invalid vDk0",
    "channel element",
    "Reserved bit set",
    "Error decoding AAC frame",
)


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True)


# libavcodecの出力がこの割合を超えて無音なら、警告が無くても中身を疑う。
SUSPICIOUS_SILENCE = 0.20


@dataclass
class Report:
    path: Path
    codec: str | None
    duration: float
    complaints: int
    silence: float
    apple_silence: float | None = None   # 突き合わせをした場合のみ

    @property
    def silence_ratio(self) -> float:
        return self.silence / self.duration if self.duration else 0.0

    @property
    def apple_silence_ratio(self) -> float | None:
        if self.apple_silence is None or not self.duration:
            return None
        return self.apple_silence / self.duration

    @property
    def broken(self) -> bool:
        if self.complaints > 0:
            return True
        # 警告は出ていないが無音が多い場合。Appleの復号では鳴っているなら、
        # 無音はlibavcodec側の失敗であって素材の仕様ではない。
        a = self.apple_silence_ratio
        return a is not None and self.silence_ratio > SUSPICIOUS_SILENCE and a < self.silence_ratio / 2

    @property
    def reason(self) -> str:
        if self.complaints > 0:
            return f"警告 {self.complaints:5d}行"
        return "両デコーダの不一致"


def probe(path: Path) -> tuple[str | None, float]:
    p = run(["ffprobe", "-v", "error", "-print_format", "json",
             "-show_format", "-show_streams", str(path)])
    try:
        d = json.loads(p.stdout)
    except json.JSONDecodeError:
        return None, 0.0
    audio = next((s for s in d.get("streams", []) if s.get("codec_type") == "audio"), None)
    try:
        dur = float(d.get("format", {}).get("duration", 0))
    except (TypeError, ValueError):
        dur = 0.0
    return (audio or {}).get("codec_name"), dur


def inspect(path: Path) -> Report:
    """libavcodecで音声を通しで復号し、警告の数と無音の量を測る。

    無音の測定は silencedetect を使うので info レベルで走らせる必要がある
    （warning レベルだと silence_duration の行ごと消える）。
    """
    codec, dur = probe(path)
    if codec is None:
        return Report(path, None, dur, 0, 0.0)

    complaints, silence = decode_with_ffmpeg(path)
    r = Report(path, codec, dur, complaints, silence)

    # 警告が無いのに無音が多いときだけ、Appleの復号と突き合わせる。
    # afconvertは実際に復号するので安くはなく、疑わしい場合に限って呼ぶ。
    # 無音の量はぶれるが、両デコーダの差が2倍以上あるかどうかの判断には十分使える。
    if complaints == 0 and r.silence_ratio > SUSPICIOUS_SILENCE:
        r.apple_silence = decode_with_apple(path)
    return r


def decode_with_ffmpeg(path: Path) -> tuple[int, float]:
    """libavcodecで通しで復号し、(警告行数, 無音の秒数) を返す。

    無音の測定は silencedetect を使うので info レベルで走らせる必要がある
    （warning レベルだと silence_duration の行ごと消える）。

    警告行数は完全に再現する（同じファイルなら常に同じ値）が、無音の秒数は
    実行ごとに大きくぶれる ―― 実測で同一ファイルが787〜987秒の範囲で変動した。
    破損データを食ったあとのlibavcodecが未定義の状態で動いているためで、
    無音は「どれくらい実害が出るか」の目安として見るに留め、判定には使わない。
    """
    p = run(["ffmpeg", "-v", "info", "-i", str(path), "-map", "0:a:0",
             "-af", "silencedetect=noise=-90dB:d=0.5", "-f", "null", "-"])
    err = p.stderr
    complaints = sum(1 for line in err.splitlines()
                     if any(s in line for s in DECODER_COMPLAINTS))
    silence = sum(float(m) for m in re.findall(r"silence_duration:\s*([0-9.]+)", err))
    return complaints, silence


def decode_with_apple(path: Path) -> float | None:
    """AudioToolboxで復号したときの無音の秒数。復号できなければNone。"""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "a.wav"
        if run(["afconvert", "-f", "WAVE", "-d", "LEI16",
                str(path), str(wav)]).returncode != 0 or not wav.exists():
            return None
        p = run(["ffmpeg", "-v", "info", "-i", str(wav),
                 "-af", "silencedetect=noise=-90dB:d=0.5", "-f", "null", "-"])
        return sum(float(m) for m in re.findall(r"silence_duration:\s*([0-9.]+)", p.stderr))


def fix(src: Path, dst: Path, bitrate: int, keep_all: bool) -> str | None:
    """srcの音声をApple経由で作り直し、映像はコピーしてdstに書く。"""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp_audio = dst.with_name(dst.name + ".fix.m4a")
    tmp_out = dst.with_name(dst.name + ".fix" + dst.suffix)
    try:
        # ここが要点。afconvertは入力の復号にAudioToolboxを使うので、
        # libavcodecが読めないストリームでも中身を取り出せる。
        # -s 2 は制約付きVBR（-b が上限）。帯域の狭い素材では自動的に節約される。
        p = run(["afconvert", "-f", "mp4f", "-d", "aac", "-b", str(bitrate),
                 "-s", "2", str(src), str(tmp_audio)])
        if p.returncode != 0 or not tmp_audio.exists():
            return f"afconvertが失敗: {p.stderr.strip().splitlines()[-1][:100] if p.stderr.strip() else '出力なし'}"

        maps = ["-map", "0:v", "-map", "1:a:0"] if keep_all else ["-map", "0:v:0", "-map", "1:a:0"]
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-i", str(tmp_audio),
               *maps, "-c", "copy"]
        if dst.suffix.lower() in {".mp4", ".m4v", ".mov"}:
            cmd += ["-movflags", "+faststart"]
        cmd.append(str(tmp_out))
        p = run(cmd)
        if p.returncode != 0:
            return f"多重化が失敗: {p.stderr.strip().splitlines()[-1][:100] if p.stderr.strip() else ''}"

        # 検証: 尺が元と合っていて、デコーダの警告が消えていること
        _, d_src = probe(src)
        after = inspect(tmp_out)
        if abs(d_src - after.duration) > 1.0:
            return f"尺が合わない {d_src:.1f}s → {after.duration:.1f}s"
        if after.complaints:
            return f"警告が残っている（{after.complaints}件）"

        tmp_out.replace(dst)
        return None
    finally:
        tmp_audio.unlink(missing_ok=True)
        tmp_out.unlink(missing_ok=True)


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def collect(inputs: list[Path], outdir: Path, recursive: bool) -> list[Path]:
    out = outdir.resolve()
    found: list[Path] = []
    for item in inputs:
        item = item.resolve()
        if item.is_dir():
            it = item.rglob("*") if recursive else item.glob("*")
            found += [q for q in it
                      if q.is_file() and q.suffix.lower() in VIDEO_SUFFIXES
                      and out not in q.parents and q != out]
        elif item.is_file():
            found.append(item)
    return sorted(set(found))


def common_root(paths: list[Path]) -> Path:
    if len(paths) == 1:
        return paths[0].parent
    import os
    return Path(os.path.commonpath([str(p.parent) for p in paths]))


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="libavcodecが復号できない音声をAppleのデコーダ経由で作り直す",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("inputs", nargs="+", type=Path, help="動画ファイルまたはディレクトリ")
    p.add_argument("-o", "--outdir", type=Path, default=Path("fixed"), help="出力先")
    p.add_argument("--check", action="store_true", help="調べるだけで書き出さない")
    p.add_argument("-b", "--bitrate", type=int, default=128000, help="作り直す音声のbps")
    p.add_argument("--all-video-streams", action="store_true",
                   help="映像トラックを全部残す（既定は先頭のみ）")
    p.add_argument("--no-recursive", dest="recursive", action="store_false",
                   help="サブディレクトリを辿らない")
    p.add_argument("-j", "--jobs", type=int, default=4, help="検査の並列数")
    p.add_argument("-v", "--verbose", action="store_true", help="正常なファイルも表示する")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    if sys.platform != "darwin":
        print("macOS専用です（Appleのデコーダを使うため）", file=sys.stderr)
        return 1
    for tool in ("afconvert", "ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            print(f"{tool} が見つかりません", file=sys.stderr)
            return 1

    args = parse_args(argv)
    outdir = args.outdir.resolve()
    srcs = collect(args.inputs, outdir, args.recursive)
    if not srcs:
        print("対象の動画が見つかりませんでした", file=sys.stderr)
        return 1

    print(f"{len(srcs)} 本を検査中…", flush=True)
    reports: list[Report] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(args.jobs, 1)) as ex:
        for r in ex.map(inspect, srcs):
            reports.append(r)
            if r.codec is None:
                if args.verbose:
                    print(f"  音声なし  {r.path.name}", flush=True)
            elif r.broken:
                print(f"  {r.reason} / 無音およそ {r.silence_ratio:3.0%}"
                      f"  {r.path.name}", flush=True)
            elif args.verbose:
                extra = ""
                if r.apple_silence_ratio is not None:
                    extra = f"（無音 {r.silence_ratio:.0%} だがAppleでも同様）"
                print(f"  正常                {extra:22} {r.path.name}", flush=True)

    broken = [r for r in reports if r.broken]
    print(f"\n破損: {len(broken)} / {len(srcs)} 本")
    if not broken:
        return 0
    if args.check:
        print("（--check のため書き出しません）")
        return 0

    root = common_root([r.path for r in reports])
    print(f"\n音声を作り直します（映像はコピー） → {outdir}")
    ok = failed = 0
    for i, r in enumerate(broken, 1):
        try:
            rel = r.path.relative_to(root)
        except ValueError:
            rel = Path(r.path.name)
        dst = outdir / rel
        if dst.resolve() == r.path:
            print(f"  [{i}/{len(broken)}] 出力先が入力と同じなので飛ばす: {rel}")
            failed += 1
            continue
        err = fix(r.path, dst, args.bitrate, args.all_video_streams)
        if err:
            print(f"  [{i}/{len(broken)}] 失敗 {rel}: {err}", flush=True)
            failed += 1
        else:
            print(f"  [{i}/{len(broken)}] 完了 {rel} "
                  f"({human(r.path.stat().st_size)} → {human(dst.stat().st_size)})", flush=True)
            ok += 1

    print(f"\n復旧 {ok} 本 / 失敗 {failed} 本")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
