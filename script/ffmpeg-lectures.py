#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""スライド主体のWeb講演動画をHEVC/AV1で再圧縮する。

想定する素材の特徴:
  - 画面のほとんどが静止したスライド（動きが極端に少ない）
  - 細かい文字が多く、解像度と文字の可読性は落とせない
  - 音声はナレーションのみ。ステレオでも左右が同一（デュアルモノ）なことが多い

これらに合わせて長いGOP・強めのAQ・保守的なCRFを既定値にしてある。
入力は都度ffprobeで解析し、解像度・フレームレート・音声コーデック・チャンネル構成に
応じて設定を組み立てるので、この種の素材以外にもそのまま使える。

主な使い分け:
  ffmpeg-lectures.py . -o out                配布用。HEVC + AACコピー + MP4
  ffmpeg-lectures.py . -o out --apple        写真.app/ファイル.appで開ける形に固定
  ffmpeg-lectures.py . -o out --av1          自分用アーカイブ。AV1 + Opus + WebM
  ffmpeg-lectures.py . -o out --apple --av1  AV1のままApple機で開ける形（A17 Pro/M3以降）

元ファイルは決して変更せず、-o 配下にディレクトリ構成を複製して書き出す。
"""

from __future__ import annotations

import argparse
import functools
import json
import re
import shlex
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

VIDEO_SUFFIXES = frozenset({".mp4", ".mov", ".m4v", ".mkv", ".avi", ".wmv", ".flv", ".ts", ".webm"})

# 左右チャンネル差がこの値(dBFS)を下回れば実質デュアルモノとみなす
DUAL_MONO_MAX_DB = -60.0
# 非可逆音声がこのビットレート以下なら、再エンコードは世代劣化を足すだけなのでコピーする
LOSSY_COPY_MAX_BITRATE = 256_000
# 音声解析に使うサンプル長（秒）
AUDIO_PROBE_SECONDS = 180

# MP4に入れても広く再生できる音声コーデック。Opus/Vorbisは規格上MP4に入るが
# QuickTime/Safariが再生できないため、コピーせずAACに変換する。
MP4_SAFE_AUDIO_CODECS = frozenset({"aac", "mp3", "ac3", "eac3", "alac"})

# --apple 指定時に「そのままコピーしてよい」と認める音声コーデック。
# MP3やAC3もMP4コンテナには入るが、AVFoundationでの扱いが環境によって怪しいので
# QuickTime/写真/iOSで確実に鳴る2つだけに絞る。
APPLE_SAFE_AUDIO_CODECS = frozenset({"aac", "alac"})

# CRFの目盛りはコーデック間で共通ではない。この2つは実測で同等品質になる値
# （EGPA: 45.3dB対45.0dB、小児疫学: 51.3dB対51.6dB）から、やや高画質側に振ってある。
DEFAULT_CRF = {"libx265": 22, "libsvtav1": 44}
DEFAULT_PRESET = {"libx265": "medium", "libsvtav1": "6"}

# Opusは音声において AAC-LC の1.5〜2倍効率が良いので、同品質をより少ないビットで買える。
# 64k mono ≒ 128k AAC mono。
DEFAULT_AUDIO_BITRATE = {"aac": {1: 128, 2: 128}, "libopus": {1: 64, 2: 96}}

# 非可逆コーデック。これらは joint stereo（M/S）を使うので、左右が同一なら
# 右チャンネルのコストはほぼゼロ。つまりステレオのままコピーしても無駄は少ない。
# 逆にPCM/FLAC等の可逆・非圧縮は左右同一でも律儀に倍のデータを食うため、
# デュアルモノならモノ化の効果が非常に大きい。
LOSSY_AUDIO_CODECS = frozenset({
    "aac", "mp3", "mp2", "opus", "vorbis", "ac3", "eac3", "wmav1", "wmav2",
    "amr_nb", "amr_wb", "speex", "atrac3", "dts", "cook", "sipr", "nellymoser",
})


class ProbeError(RuntimeError):
    pass


@dataclass(frozen=True)
class AudioInfo:
    codec: str | None
    channels: int
    sample_rate: int
    bitrate: int | None

    @property
    def lossy(self) -> bool:
        """非可逆コーデックか。可逆・非圧縮ならモノ化・再エンコードの効果が大きい。"""
        return (self.codec or "").lower() in LOSSY_AUDIO_CODECS


@dataclass(frozen=True)
class MediaInfo:
    path: Path
    duration: float
    size: int
    video_codec: str
    width: int
    height: int
    fps: float
    video_bitrate: int | None
    audio: AudioInfo | None


@dataclass(frozen=True)
class AudioPlan:
    args: list[str]
    note: str
    codec: str = "copy"   # "copy" / "aac" / "libopus"

    @property
    def needs_matroska(self) -> bool:
        """OpusをMP4に入れるとmacOSがデコードできない（実測でafconvertが失敗）ため避ける。

        規格上はISOBMFFへのOpusカプセル化が定義されているが、AVFoundationに
        Opusデコーダが無いのでQuickTimeでは音が出ない。
        """
        return self.codec == "libopus"


@dataclass
class Result:
    src: Path
    dst: Path
    ok: bool
    message: str
    src_size: int = 0
    dst_size: int = 0


def run_json(cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise ProbeError(proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "ffprobe failed")
    return json.loads(proc.stdout)


def parse_fraction(value: str | None) -> float:
    """'30000/1001' 形式のフレームレート表記を float にする。"""
    if not value or "/" not in value:
        try:
            return float(value) if value else 0.0
        except ValueError:
            return 0.0
    num, den = value.split("/", 1)
    try:
        n, d = float(num), float(den)
    except ValueError:
        return 0.0
    return n / d if d else 0.0


def to_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@functools.lru_cache(maxsize=None)
def measure_channel_difference(path: Path) -> float:
    """L-R の最大音量を dBFS で返す。無音（＝左右同一）なら大きな負の値。

    音声を実際にデコードするので安くはない。再エンコードすると決まった後に
    「ついでにモノへまとめられるか」を判断するためだけに呼ぶこと。
    コピーで済む入力に対しては呼ばれない。
    """
    filt = (
        "[0:a]channelsplit=channel_layout=stereo[l][r];"
        "[l][r]amerge=inputs=2,aeval=val(0)-val(1):c=mono,volumedetect"
    )
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-t", str(AUDIO_PROBE_SECONDS), "-i", str(path),
         "-filter_complex", filt, "-f", "null", "-"],
        capture_output=True, text=True,
    )
    matches = re.findall(r"max_volume:\s*(-?\d+(?:\.\d+)?) dB", proc.stderr)
    if not matches:
        return 0.0  # 判定できなければ「差がある」側に倒す
    return min(float(m) for m in matches)


def is_dual_mono(path: Path, audio: AudioInfo) -> bool:
    """左右が同一で、1chにまとめても情報が失われないか。"""
    return audio.channels == 2 and measure_channel_difference(path) < DUAL_MONO_MAX_DB


def estimate_audio_bitrate(path: Path, seconds: int = 60) -> int | None:
    """ストリームのbit_rateが未記載のとき（mkv等でよくある）、実パケットから推定する。"""
    # csv出力は要求した順ではなくffprobe内部のフィールド順で並ぶため、jsonで受ける
    try:
        data = run_json([
            "ffprobe", "-v", "error", "-print_format", "json", "-select_streams", "a:0",
            "-read_intervals", f"%+{seconds}",
            "-show_entries", "packet=size,duration_time", str(path),
        ])
    except (ProbeError, json.JSONDecodeError):
        return None

    total_bytes = 0
    total_time = 0.0
    for packet in data.get("packets", []):
        size, duration = to_int(packet.get("size")), packet.get("duration_time")
        if size is None or duration is None:
            continue
        try:
            total_time += float(duration)
        except ValueError:
            continue
        total_bytes += size

    if total_time <= 0:
        return None
    return int(total_bytes * 8 / total_time)


def probe(path: Path) -> MediaInfo:
    data = run_json([
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(path),
    ])
    fmt = data.get("format", {})
    streams = data.get("streams", [])

    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None:
        raise ProbeError("映像ストリームが見つかりません")

    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    audio: AudioInfo | None = None
    if audio_stream is not None:
        audio = AudioInfo(
            codec=audio_stream.get("codec_name"),
            channels=to_int(audio_stream.get("channels")) or 1,
            sample_rate=to_int(audio_stream.get("sample_rate")) or 48_000,
            bitrate=to_int(audio_stream.get("bit_rate")) or estimate_audio_bitrate(path),
        )

    return MediaInfo(
        path=path,
        duration=float(fmt.get("duration") or 0.0),
        size=to_int(fmt.get("size")) or path.stat().st_size,
        video_codec=video.get("codec_name", "?"),
        width=to_int(video.get("width")) or 0,
        height=to_int(video.get("height")) or 0,
        fps=parse_fraction(video.get("avg_frame_rate") or video.get("r_frame_rate")),
        video_bitrate=to_int(video.get("bit_rate")),
        audio=audio,
    )


def build_video_args(info: MediaInfo, args: argparse.Namespace) -> list[str]:
    fps = info.fps if info.fps > 0 else 30.0
    # スライドは動かないのでGOPを長くとる。ただしシークが辛くならない範囲に収める。
    keyint = max(int(round(fps * args.gop_seconds)), 1)

    out: list[str] = []
    if args.encoder == "libx265":
        out += [
            "-c:v", "libx265",
            "-preset", args.preset,
            "-crf", str(args.crf),
            "-x265-params", ":".join([
                f"keyint={keyint}",
                f"min-keyint={max(int(round(fps)), 1)}",
                "aq-mode=3",          # 平坦な背景上の細い文字にビットを回す
                "psy-rd=1.0",
                "rc-lookahead=60",
                "bframes=6",
                "log-level=error",
            ]),
        ]
    else:  # libsvtav1
        # 同品質ならHEVCの半分程度で済むが、再生環境を選ぶ。
        # screen content mode (scm=1) は測定上ほぼ無効果だったので使わない
        # ―― 日本語のアンチエイリアス文字だけでパレットモードの色数上限を超えるため。
        out += [
            "-c:v", "libsvtav1",
            "-preset", args.preset,
            "-crf", str(args.crf),
            "-g", str(keyint),
        ]

    if args.max_height and info.height > args.max_height:
        # 文字の可読性優先なので既定では縮小しない。指定時のみ偶数寸法へ丸めて縮小。
        out += ["-vf", f"scale=-2:{args.max_height}:flags=lanczos"]

    out += ["-pix_fmt", "yuv420p"]
    if args.encoder == "libx265":
        # QuickTime等がHEVCと認識するためのブランド。AV1(av01)には不要かつ有害。
        out += ["-tag:v", "hvc1"]
    return out


# WebMはMatroskaのサブセットで、収容できるコーデックが限られる。
WEBM_VIDEO_CODECS = frozenset({"libsvtav1", "libvpx-vp9", "libvpx"})
WEBM_AUDIO_CODECS = frozenset({"libopus", "libvorbis"})


def container_suffix(plan: AudioPlan, args: argparse.Namespace) -> str:
    """出力コンテナの拡張子。映像・音声コーデックの組み合わせで決まる。"""
    if args.container != "auto":
        return f".{args.container}"
    if not plan.needs_matroska:
        return ".mp4"
    # Opusを使う場合。AV1と組めばWebMに収まり、こちらの方が対応環境が広い。
    # HEVC+OpusはWebMに入らないのでMKVにする。
    if args.encoder in WEBM_VIDEO_CODECS and plan.codec in WEBM_AUDIO_CODECS:
        return ".webm"
    return ".mkv"


def resolve_audio_codec(args: argparse.Namespace) -> str:
    """再エンコードする場合に使う音声コーデック。

    AV1を選んだ場合はアーカイブ用途とみなし、対になるOpusを既定にする。
    映像が半分になると音声が容量の約半分を占めるようになるため。
    """
    if args.audio_codec == "opus":
        return "libopus"
    if args.audio_codec == "aac":
        return "aac"
    return "libopus" if args.encoder == "libsvtav1" else "aac"


def build_audio_args(info: MediaInfo, args: argparse.Namespace) -> AudioPlan:
    audio = info.audio
    if audio is None:
        return AudioPlan(["-an"], "音声なし")

    codec = (audio.codec or "").lower()
    safe_codecs = APPLE_SAFE_AUDIO_CODECS if args.apple else MP4_SAFE_AUDIO_CODECS
    mp4_safe = codec in safe_codecs
    unsafe_reason = "はApple環境で確実に鳴らない" if args.apple else "はMP4で再生できない"
    kbps = audio.bitrate // 1000 if audio.bitrate else None
    out_codec = resolve_audio_codec(args)

    def encode(channels: int, reason: str) -> AudioPlan:
        override = args.mono_bitrate if channels == 1 else args.audio_bitrate
        target = override if override else DEFAULT_AUDIO_BITRATE[out_codec][channels]
        layout = "mono" if channels == 1 else "stereo"
        name = "opus" if out_codec == "libopus" else out_codec
        return AudioPlan(
            ["-c:a", out_codec, "-b:a", f"{target}k", "-ac", str(channels)],
            f"{name} {target}k {layout} ({reason})",
            codec=out_codec,
        )

    def copy(reason: str) -> AudioPlan:
        return AudioPlan(["-c:a", "copy"], f"copy ({reason})")

    if args.audio_mode == "mono":
        return encode(1, "指定")
    if args.audio_mode == "stereo":
        return encode(min(audio.channels, 2), "指定")
    if args.audio_mode == "prefer-copy":
        if mp4_safe:
            return copy(f"{codec} {audio.channels}ch")
        return encode(min(audio.channels, 2), f"{codec}{unsafe_reason}")

    # --- auto ---
    # Opusを選んだ場合はアーカイブ目的として容量を優先し、コピーせず必ず変換する。
    # AAC 126k → Opus 64k は非可逆から非可逆への再エンコードなので世代劣化が1回乗るが、
    # AV1で映像が半減すると音声が容量の約半分を占めるため、そこを詰める判断。
    if out_codec == "libopus":
        return encode(
            1 if (audio.channels > 1 and is_dual_mono(info.path, audio)) else min(audio.channels, 2),
            f"{codec} {kbps}kから変換" if kbps else f"{codec}から変換",
        )

    # コピーで済むかを先に判定する。左右チャンネル差の実測は音声のデコードを伴うので、
    # 再エンコードが確定してから（＝下の downmixed() の中でだけ）行う。
    if audio.lossy and mp4_safe:
        if audio.bitrate is None:
            return copy(f"{codec}, bitrate不明")
        if audio.bitrate <= LOSSY_COPY_MAX_BITRATE:
            # joint stereo（M/S）なので、左右が同一なら差分チャンネルは全ゼロで
            # 右chのコストはほぼゼロ。モノ化しても大して減らず世代劣化だけが増える。
            return copy(f"{codec} {kbps}k")

    # ここから先は再エンコードが確定。ついでにモノへまとめられるなら、まとめる。
    def downmixed() -> int:
        return 1 if is_dual_mono(info.path, audio) else min(audio.channels, 2)

    if not audio.lossy:
        # PCM/FLAC等。joint stereoではないので左右同一でもデータ量は倍のまま。
        # モノ化と圧縮の効果がどちらも大きい。
        return encode(downmixed(), f"{codec}から圧縮")
    if not mp4_safe:
        return encode(downmixed(), f"{codec}{unsafe_reason}")
    return encode(downmixed(), f"{kbps}kから圧縮")


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024 or unit == "TB":
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def encode(info: MediaInfo, dst: Path, audio_plan: AudioPlan, args: argparse.Namespace) -> Result:
    src = info.path
    tmp = dst.with_name(dst.name + ".part" + dst.suffix)

    cmd = [
        "ffmpeg", "-y", "-nostdin",
        *(["-v", "info", "-stats"] if args.verbose else ["-v", "error"]),
        "-i", str(src),
        "-map", "0:v:0",
        *build_video_args(info, args),
    ]
    if info.audio is not None:
        cmd += ["-map", "0:a:0", *audio_plan.args]
    else:
        cmd += ["-an"]
    if dst.suffix == ".mp4":
        cmd += ["-movflags", "+faststart"]
    cmd += [str(tmp)]

    if args.dry_run:
        print(f"[dry-run] {src.name}\n          audio: {audio_plan.note}\n          {shlex.join(cmd)}")
        return Result(src, dst, True, "dry-run", info.size, 0)

    dst.parent.mkdir(parents=True, exist_ok=True)
    if args.verbose:
        # 進捗をそのまま流したいので捕捉しない
        print(f"--- {src.name}\n    audio: {audio_plan.note}\n    {shlex.join(cmd)}", flush=True)
        proc = subprocess.run(cmd)
        stderr = ""
    else:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        stderr = proc.stderr

    if proc.returncode != 0:
        tmp.unlink(missing_ok=True)
        tail = stderr.strip().splitlines()
        return Result(src, dst, False, tail[-1] if tail else f"ffmpeg failed ({proc.returncode})",
                      info.size, 0)

    # 尺が合っているかで壊れた出力を弾く
    try:
        out_duration = probe_duration(tmp)
    except ProbeError as exc:
        tmp.unlink(missing_ok=True)
        return Result(src, dst, False, f"出力を検証できません: {exc}", info.size, 0)

    if info.duration > 0 and abs(out_duration - info.duration) > 1.0:
        tmp.unlink(missing_ok=True)
        return Result(src, dst, False, f"尺が不一致 ({out_duration:.1f}s vs {info.duration:.1f}s)", info.size, 0)

    tmp.replace(dst)
    return Result(src, dst, True, audio_plan.note, info.size, dst.stat().st_size)


def probe_duration(path: Path) -> float:
    data = run_json([
        "ffprobe", "-v", "error", "-print_format", "json", "-show_format", str(path),
    ])
    return float(data.get("format", {}).get("duration") or 0.0)


def collect_inputs(roots: list[Path], outdir: Path, recursive: bool) -> list[Path]:
    """入力を集める。出力先が入力ツリーの内側にある場合、そこは走査しない。

    `compress_lectures.py . -o compressed` のように出力先を入力の内側に置くのは
    自然な使い方だが、素朴に走査すると2回目の実行で出力済みファイルを入力として
    拾い、再圧縮してしまう（中断時に残る *.part.mp4 も同様）。
    """
    def under_outdir(p: Path) -> bool:
        return p == outdir or outdir in p.parents

    found: list[Path] = []
    for root in roots:
        if root.is_file():
            found.append(root)
        elif root.is_dir():
            it = root.rglob("*") if recursive else root.glob("*")
            found += [p for p in it
                      if p.is_file() and p.suffix.lower() in VIDEO_SUFFIXES and not under_outdir(p)]
    return sorted(set(found))


def destination_for(src: Path, roots: list[Path], outdir: Path, suffix: str = ".mp4") -> Path:
    """入力ディレクトリ構成を出力先に写す。"""
    for root in roots:
        if root.is_dir():
            try:
                return (outdir / src.relative_to(root)).with_suffix(suffix)
            except ValueError:
                continue
    return (outdir / src.name).with_suffix(suffix)


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="スライド主体の講演動画をHEVC/AV1で再圧縮する",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("inputs", nargs="+", type=Path, help="入力ファイルまたはディレクトリ")
    p.add_argument("-o", "--outdir", type=Path, default=Path("compressed"), help="出力先ディレクトリ")
    enc = p.add_mutually_exclusive_group()
    enc.add_argument("--hevc", dest="encoder", action="store_const", const="libx265",
                     help="HEVC/H.265 (libx265)。互換性重視の既定")
    enc.add_argument("--av1", dest="encoder", action="store_const", const="libsvtav1",
                     help="AV1 (SVT-AV1)。同品質でHEVCの約半分になるが再生環境を選ぶ。"
                          "音声も既定でOpusになる")
    p.set_defaults(encoder="libx265")
    p.add_argument("--apple", action="store_true",
                   help="写真.app / ファイル.app / QuickTime が開ける入れ物と音声に固定する"
                        "（MP4 + AAC）。映像コーデックは --hevc / --av1 で選ぶ")
    p.add_argument("--crf", type=int, default=None,
                   help=f"CRF（小さいほど高画質）。目盛りはコーデックごとに異なる。"
                        f"既定: {' / '.join(f'{k}={v}' for k, v in DEFAULT_CRF.items())}")
    p.add_argument("--preset", default=None,
                   help=f"エンコーダのpreset。"
                        f"既定: {' / '.join(f'{k}={v}' for k, v in DEFAULT_PRESET.items())}")
    p.add_argument("--gop-seconds", type=float, default=10.0, help="キーフレーム間隔（秒）")
    p.add_argument("--max-height", type=int, default=0,
                   help="この高さを超える映像を縮小する（0=縮小しない。文字可読性のため既定は無効）")
    p.add_argument("--audio-mode", choices=["auto", "prefer-copy", "mono", "stereo"], default="auto",
                   help=f"auto=非可逆{LOSSY_COPY_MAX_BITRATE // 1000}k以下ならコピー、可逆なら圧縮。"
                        "prefer-copy=可能な限りコピー（MP4で再生できないコーデックのみAAC化）")
    p.add_argument("--audio-codec", choices=["auto", "aac", "opus"], default="auto",
                   help="auto=--av1ならopus、それ以外はaac")
    p.add_argument("--container", choices=["auto", "mp4", "mkv", "webm"], default="auto",
                   help="出力コンテナ。auto=AV1+Opusならwebm、他のOpusならmkv、それ以外はmp4")
    p.add_argument("--audio-bitrate", type=int, default=None,
                   help="ステレオ再エンコード時のkbps（既定: aac 128 / opus 96）")
    p.add_argument("--mono-bitrate", type=int, default=None,
                   help="モノラル再エンコード時のkbps（既定: aac 128 / opus 64）")
    p.add_argument("-j", "--jobs", type=int, default=1, help="並列実行数")
    p.add_argument("--skip-existing", action="store_true", help="出力が既にあればスキップ")
    p.add_argument("--no-recursive", dest="recursive", action="store_false", help="サブディレクトリを辿らない")
    p.add_argument("--dry-run", action="store_true", help="コマンドを表示するだけで実行しない")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="ffmpegのコマンドラインと進捗を表示する（-j 2以上では出力が混ざる）")
    args = p.parse_args(argv)
    if args.apple:
        # --apple が担うのは「入れ物と音声」だけで、映像コーデックには手を出さない。
        # MP4+AACは機種に関係なくAVFoundationが扱える一方、どの映像コーデックが
        # 再生できるかは機種依存（AV1はA17 Pro / M3以降のみ）なので、そこは
        # --hevc / --av1 の判断に委ねる。だから --apple --av1 は矛盾ではない。
        # 黙って上書きすると「指定したのに効かない」になるので、矛盾はエラーで返す。
        if args.audio_codec == "opus":
            p.error("--apple は --audio-codec opus と併用できません（AVFoundationにOpusデコーダがありません）")
        if args.container not in ("auto", "mp4"):
            p.error(f"--apple は --container {args.container} と併用できません")
        args.audio_codec, args.container = "aac", "mp4"
    if args.crf is None:
        args.crf = DEFAULT_CRF.get(args.encoder, 22)
    if args.preset is None:
        args.preset = DEFAULT_PRESET.get(args.encoder, "medium")
    if args.container == "webm" and args.encoder not in WEBM_VIDEO_CODECS:
        p.error(f"--container webm は {args.encoder} を収容できません（--av1 と併用してください）")
    return args


def main(argv: list[str]) -> int:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        print("ffmpeg / ffprobe が見つかりません", file=sys.stderr)
        return 1

    args = parse_args(argv)
    roots = [p.resolve() for p in args.inputs]
    outdir = args.outdir.resolve()
    sources = collect_inputs(roots, outdir, args.recursive)
    if not sources:
        print("対象の動画が見つかりませんでした", file=sys.stderr)
        return 1

    jobs: list[tuple[MediaInfo, Path, AudioPlan]] = []

    if args.apple and args.encoder == "libsvtav1":
        # 通すが、再生できる機種が限られることは黙っていられない。
        print("注意: AV1はA17 Pro / M3世代以降のApple機でのみ再生できます"
              "（M1・M2世代では再生できません）")
    print(f"出力先: {outdir}（元ファイルは変更しません）")
    print(f"{len(sources)} 本を解析中…")
    for src in sources:
        try:
            info = probe(src)
        except (ProbeError, json.JSONDecodeError) as exc:
            print(f"  NG     {src.name}: {exc}", file=sys.stderr)
            continue

        # コンテナは音声の計画で決まる（Opusを使うならMKV）ので、先に立てる
        plan = build_audio_args(info, args)
        dst = destination_for(src, roots, outdir, container_suffix(plan, args))
        if args.skip_existing and dst.exists():
            print(f"  skip   {src.name}")
            continue
        if dst.resolve() == src:
            print(f"  skip   {src.name}（出力先が入力と同一）")
            continue

        audio_desc = "音声なし"
        if info.audio:
            kbps = f"{info.audio.bitrate // 1000}k" if info.audio.bitrate else "?"
            audio_desc = f"{info.audio.codec} {info.audio.channels}ch {kbps}"
        print(f"  {src.name}: {info.width}x{info.height} {info.fps:.3g}fps "
              f"{info.video_codec} / {audio_desc} / {human(info.size)}")
        jobs.append((info, dst, plan))

    if not jobs:
        print("処理対象がありません")
        return 0

    results: list[Result] = []
    print(f"\n{len(jobs)} 本を {args.encoder} で圧縮します（並列 {args.jobs}）")
    with ThreadPoolExecutor(max_workers=max(args.jobs, 1)) as pool:
        futures = {pool.submit(encode, info, dst, plan, args): info for info, dst, plan in jobs}
        for done, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            results.append(result)
            if not result.ok:
                print(f"[{done}/{len(jobs)}] NG {result.src.name}: {result.message}", file=sys.stderr, flush=True)
            elif args.dry_run:
                pass
            else:
                ratio = result.dst_size / result.src_size if result.src_size else 0
                print(f"[{done}/{len(jobs)}] {result.src.name}: "
                      f"{human(result.src_size)} → {human(result.dst_size)} "
                      f"({ratio:.0%}) / {result.message}", flush=True)

    if args.dry_run:
        return 0

    ok = [r for r in results if r.ok]
    src_total = sum(r.src_size for r in ok)
    dst_total = sum(r.dst_size for r in ok)
    print(f"\n完了 {len(ok)}/{len(results)} 本")
    if src_total:
        print(f"合計 {human(src_total)} → {human(dst_total)} "
              f"({dst_total / src_total:.0%}, {human(src_total - dst_total)} 削減)")
    return 0 if len(ok) == len(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
