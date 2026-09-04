#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""動画をH.264/HEVC/AV1へ再圧縮する。単発でもディレクトリ丸ごとでも使える。

入力は都度ffprobeで解析し、解像度・フレームレート・音声コーデック・チャンネル構成に
応じて設定を組み立てる。音声はコピーで済むなら再エンコードせず、デュアルモノ
（ステレオだが左右が同一）なら1chにまとめる。出力コンテナは映像・音声の
組み合わせから決めるので、再生できない組み合わせが出来上がることはない。

単発ファイルの例:
  ffmpeg-convert.py in.mp4                       元と同じ場所に「in [hevc].mp4」
  ffmpeg-convert.py in.mp4 -s 720p -q high       720pへ縮小して高画質
  ffmpeg-convert.py in.mp4 --h264 -t animation   H.264 + tune animation
  ffmpeg-convert.py in.mp4 -o out.mp4            出力名を明示

ディレクトリの例（元ファイルは変更せず、-o 配下に構成を複製する）:
  ffmpeg-convert.py . -o out                     配布用。HEVC + AACコピー + MP4
  ffmpeg-convert.py . -o out --apple             写真.app/ファイル.appで開ける形に固定
  ffmpeg-convert.py . -o out --av1               自分用アーカイブ。AV1 + Opus + WebM
  ffmpeg-convert.py . -o out --apple --av1       AV1のままApple機で開ける形（A17 Pro/M3以降）

--lecture: スライド主体のWeb講演動画向けモード。
  - 画面のほとんどが静止したスライド（動きが極端に少ない）
  - 細かい文字が多く、解像度と文字の可読性は落とせない
  - 音声はナレーションのみ
こうした素材に合わせて、長いGOP・強めのAQ・保守的なCRFへ既定値を差し替える。

端末から実行して素材・解像度・コーデック・Apple互換を省いた場合は、どれにするかを
対話で聞く。パイプ・cron・--no-interactive では何も聞かず既定（汎用素材 + 元の解像度 +
HEVC + MP4）で走るので、バッチ実行は変わらない。
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
import tempfile
import threading
import unicodedata
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

# コーデックの通称 → ffmpegのエンコーダ名。出力ファイル名には通称を使う。
ENCODER_LIBRARIES = {"h264": "libx264", "hevc": "libx265", "av1": "libsvtav1"}
ENCODER_NAMES = {library: name for name, library in ENCODER_LIBRARIES.items()}

# 品質段階 → CRF（小さいほど高画質）。目盛りはコーデック間で共通ではない。
# 汎用素材（実写・アニメ）向け。
CRF_MAP = {
    "libx264": {"low": 30, "portable": 26, "normal": 23, "high": 20, "veryhigh": 18},
    "libx265": {"low": 35, "portable": 30, "normal": 28, "high": 24, "veryhigh": 20},
    "libsvtav1": {"low": 40, "portable": 35, "normal": 32, "high": 28, "veryhigh": 24},
}

# --lecture 用のCRF。スライドは平坦な面が広く、同じCRFでも汎用素材より破綻しにくい
# 一方で文字の可読性は落とせないため、normal を保守的に置いてある。
# libx265=22 と libsvtav1=44 は実測で同等品質になる値
# （EGPA: 45.3dB対45.0dB、小児疫学: 51.3dB対51.6dB）から、やや高画質側に振ったもの。
# libx264 の段は未実測で、x265比 -3 の経験的な差から置いた値。
LECTURE_CRF_MAP = {
    "libx264": {"low": 25, "portable": 22, "normal": 19, "high": 17, "veryhigh": 15},
    "libx265": {"low": 28, "portable": 25, "normal": 22, "high": 20, "veryhigh": 18},
    "libsvtav1": {"low": 50, "portable": 47, "normal": 44, "high": 40, "veryhigh": 36},
}
QUALITY_CHOICES = ["low", "portable", "normal", "high", "veryhigh"]
DEFAULT_QUALITY = "normal"

DEFAULT_PRESET = {"libx264": "medium", "libx265": "medium", "libsvtav1": "6"}

# --lecture のキーフレーム間隔（秒）。スライドは動かないのでGOPを長くとれるが、
# シークが辛くならない範囲に収める。汎用素材ではエンコーダの既定に任せる。
LECTURE_GOP_SECONDS = 10.0

# -s/--size の別名 → 短辺の目標画素数。'source' は縮小しない。数値も直接受ける。
SIZE_ALIASES = {"480p": 480, "720p": 720, "1080p": 1080, "1440p": 1440, "2160p": 2160}
SIZE_SOURCE = "source"

# 対話モードで提示する解像度（値, 説明）。先頭が既定。
# 縮小は文字の可読性を確実に落とすので、既定は「元のまま」に置く。
SIZE_CHOICES = [
    (SIZE_SOURCE, "元のまま — 縮小しない"),
    ("1080p", "1080p — 短辺が1080pxを超える映像だけ縮小"),
    ("720p", "720p — 短辺が720pxを超える映像だけ縮小"),
    ("480p", "480p — 短辺が480pxを超える映像だけ縮小"),
]

# 対話モードで提示する映像コーデック（値, 説明）。先頭が既定。
ENCODER_CHOICES = [
    ("libx265", "HEVC / H.265 — 配布用。どの機種でも再生できる"),
    ("libsvtav1", "AV1 — 自分用アーカイブ。同品質で約半分だが再生環境を選ぶ"),
    ("libx264", "H.264 — 最も互換性が高い。同品質だと最も大きい"),
]
DEFAULT_ENCODER = ENCODER_CHOICES[0][0]

# 対話モードで提示する素材の種類（値, 説明）。先頭が既定。
CONTENT_CHOICES = [
    ("general", "汎用 — 実写・アニメなど。エンコーダの既定に近い設定"),
    ("lecture", "講演スライド — 静止画主体で細かい文字が多い。長いGOP・強めのAQ"),
]
DEFAULT_CONTENT = CONTENT_CHOICES[0][0]

# -t/--tune が効くエンコーダ。ffmpegのlibsvtav1ラッパーは tune オプションを
# 公開していないため、-tune を渡してもエラーにならず黙って無視される。
# 「指定したのに効かない」を避けるため、AV1では -t をエラーで返す。
# （SVT-AV1自身の tune=0/1/2 は -svtav1-params tune=N でしか触れない別物）
TUNE_ENCODERS = frozenset({"libx264", "libx265"})

# Opusは音声において AAC-LC の1.5〜2倍効率が良いので、同品質をより少ないビットで買える。
# 64k mono ≒ 128k AAC mono。
DEFAULT_AUDIO_BITRATE = {"aac": {1: 128, 2: 128}, "libopus": {1: 64, 2: 96}}

# ffmpegのエンコーダ名 → ストリームのcodec_name。表示とコンテナ適合判定で使う。
ENCODER_CODEC_NAME = {"libopus": "opus", "libvorbis": "vorbis", "aac": "aac"}

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


# x264とx265はエンコーダ固有パラメータを専用フラグで受ける。SVT-AV1は持たない。
PARAMS_FLAG = {"libx264": "-x264-params", "libx265": "-x265-params"}


def keyint_frames(info: MediaInfo, gop_seconds: float) -> int:
    """GOP長（秒）をフレーム数に直す。フレームレートが読めなければ30fps扱い。"""
    fps = info.fps if info.fps > 0 else 30.0
    return max(int(round(fps * gop_seconds)), 1)


def scale_filter(info: MediaInfo, target_short_side: int) -> str | None:
    """短辺を target_short_side に合わせるスケールフィルタ。不要ならNone。

    「720p」は横長なら高さ720、縦長なら幅720を指す。縦動画でも期待どおりの
    大きさになるよう、常に短辺を基準にする。アスペクト比は変えない。
    拡大は画質を上げないので行わず、元より小さい指定のときだけ縮小する。
    寸法は偶数へ丸める（-2）。yuv420pは奇数寸法を扱えないため。
    """
    if target_short_side <= 0:
        return None
    short_side = min(info.width, info.height)
    if short_side <= 0 or short_side <= target_short_side:
        return None
    if info.height > info.width:
        return f"scale={target_short_side}:-2:flags=lanczos"
    return f"scale=-2:{target_short_side}:flags=lanczos"


def build_video_args(info: MediaInfo, args: argparse.Namespace) -> list[str]:
    out = ["-c:v", args.encoder, "-preset", args.preset, "-crf", str(args.crf)]

    # AV1では -tune が黙って無視されるため parse_args で弾いてある。
    # ここに来る args.tune は x264/x265 に渡る値だけ。
    if args.tune:
        out += ["-tune", args.tune]

    if args.encoder == "libsvtav1":
        # 同品質ならHEVCの半分程度で済むが、再生環境を選ぶ。
        # screen content mode (scm=1) は測定上ほぼ無効果だったので使わない
        # ―― 日本語のアンチエイリアス文字だけでパレットモードの色数上限を超えるため。
        if args.gop_seconds:
            out += ["-g", str(keyint_frames(info, args.gop_seconds))]
    else:
        params: list[str] = []
        if args.gop_seconds:
            params += [
                f"keyint={keyint_frames(info, args.gop_seconds)}",
                f"min-keyint={keyint_frames(info, 1.0)}",
            ]
        if args.lecture:
            # 平坦な背景上の細い文字にビットを回す
            params += ["aq-mode=3", "rc-lookahead=60", "bframes=6"]
            if args.encoder == "libx265":
                # x264のpsy-rdは2値指定で既定が既に1.0なので、x265だけ明示する
                params.append("psy-rd=1.0")
        if args.encoder == "libx265":
            params.append("log-level=error")   # x265は既定で冗長
        if params:
            out += [PARAMS_FLAG[args.encoder], ":".join(params)]

    scale = scale_filter(info, args.size)
    if scale:
        out += ["-vf", scale]

    out += ["-pix_fmt", "yuv420p"]
    if args.encoder == "libx265":
        # QuickTime等がHEVCと認識するためのブランド。AV1(av01)/H.264には不要。
        out += ["-tag:v", "hvc1"]
    return out


# WebMはMatroskaのサブセットで、収容できるコーデックが限られる。
WEBM_VIDEO_CODECS = frozenset({"libsvtav1", "libvpx-vp9", "libvpx"})
WEBM_AUDIO_CODECS = frozenset({"libopus", "libvorbis"})
WEBM_AUDIO_CODEC_NAMES = frozenset(ENCODER_CODEC_NAME[enc] for enc in WEBM_AUDIO_CODECS)


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


def output_audio_codec(plan: AudioPlan, info: MediaInfo) -> str | None:
    """出力に入る音声のcodec_name。音声を落とす場合はNone。"""
    if info.audio is None:
        return None
    if plan.codec == "copy":
        return (info.audio.codec or "").lower() or None
    return ENCODER_CODEC_NAME.get(plan.codec, plan.codec)


def container_audio_conflict(plan: AudioPlan, info: MediaInfo, suffix: str,
                             args: argparse.Namespace) -> str | None:
    """コンテナに入らない音声の組み合わせを、ffmpegを起動する前に見つける。

    --container を明示するとauto時の安全な組み合わせから外れることがある。
    そのままffmpegに渡すと "Nothing was written into output file" のような
    原因の分からないエラーで落ちるので、理由を添えて先に弾く。
    収容制限を持たないコンテナ（.mkv）は常に通す。
    """
    codec = output_audio_codec(plan, info)
    if codec is None:
        return None
    allowed = {".mp4": mp4_audio_codecs(args), ".webm": WEBM_AUDIO_CODEC_NAMES}.get(suffix)
    if allowed is None or codec in allowed:
        return None
    return (f"{suffix.lstrip('.')} に {codec} 音声は入れられません"
            f"（--container / --audio-codec / --audio-mode を見直してください）")


def mp4_audio_codecs(args: argparse.Namespace) -> frozenset[str]:
    """MP4に入れてそのまま鳴ると認める音声コーデック。--apple ならより厳しく絞る。"""
    return APPLE_SAFE_AUDIO_CODECS if args.apple else MP4_SAFE_AUDIO_CODECS


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
    mp4_safe = codec in mp4_audio_codecs(args)
    unsafe_reason = "はApple環境で確実に鳴らない" if args.apple else "はMP4で再生できない"
    kbps = audio.bitrate // 1000 if audio.bitrate else None
    out_codec = resolve_audio_codec(args)

    def encode(channels: int, reason: str) -> AudioPlan:
        override = args.mono_bitrate if channels == 1 else args.audio_bitrate
        target = override if override else DEFAULT_AUDIO_BITRATE[out_codec][channels]
        layout = "mono" if channels == 1 else "stereo"
        name = ENCODER_CODEC_NAME.get(out_codec, out_codec)
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


def display_width(text: str) -> int:
    """端末上での表示幅。日本語などの全角文字は2桁として数える。"""
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def truncate_display(text: str, limit: int) -> str:
    """表示幅が limit を超えないよう末尾を落とす。進捗行の折り返しを防ぐため。"""
    if display_width(text) <= limit:
        return text
    kept, width = [], 0
    for ch in text:
        width += 2 if unicodedata.east_asian_width(ch) in "WF" else 1
        if width > limit - 1:
            break
        kept.append(ch)
    return "".join(kept) + "…"


def clock(seconds: float) -> str:
    """秒を 1:02:03 / 2:03 形式にする。"""
    total = int(max(seconds, 0))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def parse_speed(value: str) -> float:
    """'1.52x' 形式の速度をfloatにする。N/Aなら0。"""
    try:
        return float(value.strip().rstrip("x"))
    except ValueError:
        return 0.0


class ProgressReporter:
    """エンコード中の進捗を1行にまとめて表示する。

    総尺は解析時に分かっているので、全体に対する処理済み秒数で進捗率を出せる。
    -j で並列にしても行が混ざらないよう、本数ごとではなく全体を1行だけ書き換える。
    端末以外（パイプ・cron）・--verbose・--dry-run では何もしないので、
    ログの見た目は今までどおり。
    """

    BAR_WIDTH = 20

    def __init__(self, total_duration: float, total_jobs: int, enabled: bool) -> None:
        self.total_duration = total_duration
        self.total_jobs = total_jobs
        self.enabled = enabled
        self.lock = threading.Lock()
        self.running: dict[Path, tuple[float, float]] = {}   # src -> (処理済み秒, 速度)
        self.done_duration = 0.0
        self.done_jobs = 0

    def update(self, src: Path, out_time: float, speed: float) -> None:
        """ffmpegから届いた1本分の進捗を反映する。"""
        with self.lock:
            self.running[src] = (out_time, speed)
            self._render()

    def finish(self, src: Path, duration: float) -> None:
        """1本終わった分を完了側に移す。"""
        with self.lock:
            self.running.pop(src, None)
            self.done_duration += duration
            self.done_jobs += 1

    def report(self, line: str, error: bool = False) -> None:
        """進捗行を潰さないように1行出力する。"""
        with self.lock:
            self._erase()
            print(line, file=sys.stderr if error else sys.stdout, flush=True)
            self._render()

    def close(self) -> None:
        """進捗行を消して、以降は普通の出力に戻す。"""
        with self.lock:
            self._erase()
            self.enabled = False

    def _erase(self) -> None:
        if self.enabled:
            print("\r\033[K", end="", flush=True)

    def _render(self) -> None:
        if not self.enabled:
            return
        processed = self.done_duration + sum(t for t, _ in self.running.values())
        speed = sum(s for _, s in self.running.values())

        parts = [f"[{self.done_jobs}/{self.total_jobs}]"]
        if self.total_duration > 0:
            ratio = min(processed / self.total_duration, 1.0)
            filled = round(ratio * self.BAR_WIDTH)
            parts.append(f"{ratio:4.0%} [{'█' * filled}{'░' * (self.BAR_WIDTH - filled)}]")
            parts.append(f"{clock(processed)}/{clock(self.total_duration)}")
            if speed > 0:
                parts.append(f"残り {clock((self.total_duration - processed) / speed)}")
        else:
            parts.append(f"{clock(processed)} 処理済み")
        if speed > 0:
            parts.append(f"{speed:.3g}x")
        if len(self.running) == 1:
            parts.append(next(iter(self.running)).name)
        elif len(self.running) > 1:
            parts.append(f"{len(self.running)}本並行")

        columns = shutil.get_terminal_size(fallback=(80, 24)).columns
        print("\r\033[K" + truncate_display(" ".join(parts), columns - 1), end="", flush=True)


def run_with_progress(cmd: list[str], src: Path, progress: ProgressReporter) -> tuple[int, str]:
    """ffmpegを走らせ、-progress の出力を読みながら進捗を更新する。

    stderrは一時ファイルに落とす。stdoutと同時にパイプで受けると、
    エラーが多いときにバッファが詰まって双方が止まるため。
    """
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace") as errfile:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=errfile,
                                text=True, encoding="utf-8", errors="replace")
        out_time, speed = 0.0, 0.0
        for line in proc.stdout:
            key, _, value = line.strip().partition("=")
            # 映像が終わって音声だけ流している区間などでは N/A が来る。
            # そのまま0にすると進捗が巻き戻るので、読めた値だけを更新する。
            if key == "out_time_us":
                microseconds = to_int(value)
                if microseconds is not None:
                    out_time = microseconds / 1_000_000
            elif key == "speed":
                parsed = parse_speed(value)
                if parsed > 0:
                    speed = parsed
            elif key == "progress":
                # 各ブロックの最後のキー。ここまでの値がそろったので反映する
                progress.update(src, out_time, speed)
        proc.stdout.close()
        returncode = proc.wait()
        errfile.seek(0)
        return returncode, errfile.read()


def encode(info: MediaInfo, dst: Path, audio_plan: AudioPlan, args: argparse.Namespace,
           progress: ProgressReporter) -> Result:
    src = info.path
    tmp = dst.with_name(dst.name + ".part" + dst.suffix)

    cmd = [
        "ffmpeg", "-y", "-nostdin",
        *(["-v", "info", "-stats"] if args.verbose else ["-v", "error", "-nostats"]),
        *(["-progress", "pipe:1"] if progress.enabled else []),
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
        # ffmpeg自身の進捗をそのまま流したいので捕捉しない
        print(f"--- {src.name}\n    audio: {audio_plan.note}\n    {shlex.join(cmd)}", flush=True)
        returncode, stderr = subprocess.run(cmd).returncode, ""
    elif progress.enabled:
        returncode, stderr = run_with_progress(cmd, src, progress)
    else:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        returncode, stderr = proc.returncode, proc.stderr
    progress.finish(src, info.duration)

    if returncode != 0:
        tmp.unlink(missing_ok=True)
        tail = stderr.strip().splitlines()
        return Result(src, dst, False, tail[-1] if tail else f"ffmpeg failed ({returncode})",
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


def collect_inputs(roots: list[Path], outdir: Path | None, recursive: bool) -> list[Path]:
    """入力を集める。出力先が入力ツリーの内側にある場合、そこは走査しない。

    `ffmpeg-convert.py . -o compressed` のように出力先を入力の内側に置くのは
    自然な使い方だが、素朴に走査すると2回目の実行で出力済みファイルを入力として
    拾い、再圧縮してしまう（中断時に残る *.part.mp4 も同様）。
    """
    def under_outdir(p: Path) -> bool:
        return outdir is not None and (p == outdir or outdir in p.parents)

    found: list[Path] = []
    for root in roots:
        if root.is_file():
            found.append(root)
        elif root.is_dir():
            it = root.rglob("*") if recursive else root.glob("*")
            found += [p for p in it
                      if p.is_file() and p.suffix.lower() in VIDEO_SUFFIXES and not under_outdir(p)]
    return sorted(set(found))


def parameter_suffix(info: MediaInfo, args: argparse.Namespace) -> str:
    """出力名に添える設定の要約。元ファイルと並べても、設定を変えて作り直しても区別できる。"""
    parts = []
    # 元より小さい指定でなければ縮小は起きないので、そのときは名前にも出さない。
    # 判定は scale_filter に任せて「名前と中身が食い違う」ことを防ぐ。
    if scale_filter(info, args.size):
        parts.append(f"{args.size}p")
    parts.append(ENCODER_NAMES[args.encoder])
    if args.crf_explicit:
        parts.append(f"crf{args.crf}")     # -q より強いので、こちらだけを出す
    elif args.quality != DEFAULT_QUALITY:
        parts.append(args.quality)
    if args.tune:
        parts.append(args.tune)
    if args.lecture:
        parts.append("lecture")
    return " ".join(parts)


def destination_for(info: MediaInfo, roots: list[Path], suffix: str,
                    args: argparse.Namespace) -> Path:
    """出力パスを決める。

    単発ファイルの変換では「元名 [720p hevc high].mp4」のように設定を名前に書く。
    元ファイルの隣に置いても区別でき、設定を変えて作り直しても衝突しないため。
    ディレクトリを渡された場合は元の名前のまま、入力の構成を出力先に写す。
    """
    src = info.path
    if args.output_file is not None:
        return args.output_file
    if args.single_file:
        parent = args.outdir if args.outdir is not None else src.parent
        return parent / f"{src.stem} [{parameter_suffix(info, args)}]{suffix}"
    for root in roots:
        if root.is_dir():
            try:
                return (args.outdir / src.relative_to(root)).with_suffix(suffix)
            except ValueError:
                continue
    return (args.outdir / src.name).with_suffix(suffix)


# -o をファイル名として受け取れる拡張子。ここから出力コンテナも決まる。
CONTAINER_SUFFIXES = {".mp4": "mp4", ".mkv": "mkv", ".webm": "webm"}


def resolve_output_target(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """-o をディレクトリとファイル名のどちらとして受け取るかを決める。

    出力が1本と確定しているとき（単発ファイルを1つ渡されたとき）に限り、拡張子付きの
    -o をそのまま出力パスとして扱う。ディレクトリを渡された場合や入力が複数ある場合は
    出力も複数になりうるので、-o は常に出力先ディレクトリ。`-o out` のようにどちらとも
    取れる指定はディレクトリ。

    args に次を書き込む:
      single_file  単発ファイルの変換か（出力名の付け方が変わる）
      output_file  出力パスが確定していればそのPath、でなければNone
      outdir       出力先ディレクトリ。Noneは「入力と同じ場所」
    """
    args.single_file = len(args.inputs) == 1 and args.inputs[0].is_file()
    args.output_file = None

    if args.output is None:
        # 単発ファイルは元と同じ場所へ。ディレクトリ入力は compressed/ へ。
        args.outdir = None if args.single_file else Path("compressed")
        return

    container = CONTAINER_SUFFIXES.get(args.output.suffix.lower())
    if container is None or args.output.is_dir():
        args.outdir = args.output
        return

    if not args.single_file:
        parser.error(f"-o にファイル名を指定できるのは単発ファイルの変換時だけです"
                     f"（{args.output} をディレクトリにするか、入力を1ファイルにしてください）")
    # 拡張子が出力コンテナも決める。--container で別のものを明示されていたら矛盾。
    if args.container not in ("auto", container):
        parser.error(f"-o {args.output.name} は --container {args.container} と矛盾します")
    args.container = container
    args.output_file = args.output
    args.outdir = args.output.parent


def parse_size(value: str) -> int:
    """-s/--size を短辺の目標画素数に直す。'source' と 0 は「縮小しない」。"""
    text = value.strip().lower()
    if text in ("", SIZE_SOURCE, "0"):
        return 0
    if text in SIZE_ALIASES:
        return SIZE_ALIASES[text]
    pixels = to_int(text.rstrip("p"))
    if pixels is None or pixels <= 0:
        raise argparse.ArgumentTypeError(
            f"解像度として読めません: {value}"
            f"（{' / '.join(SIZE_ALIASES)} / {SIZE_SOURCE} / 画素数）")
    return pixels


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="動画をH.264/HEVC/AV1で再圧縮する",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("inputs", nargs="+", type=Path, help="入力ファイルまたはディレクトリ")
    p.add_argument("-o", "--output", type=Path, default=None,
                   help="出力先ディレクトリ。単発ファイルの変換時は拡張子付きのファイル名も"
                        "受け取る（既定: ディレクトリ入力なら compressed/、単発ファイルなら"
                        "元と同じ場所）")
    enc = p.add_mutually_exclusive_group()
    # 既定を置かない（default=SUPPRESS）ことで「未指定」を見分け、端末実行なら聞く。
    enc.add_argument("--hevc", dest="encoder", action="store_const", const="libx265",
                     default=argparse.SUPPRESS,
                     help="HEVC/H.265 (libx265)。互換性重視の既定")
    enc.add_argument("--av1", dest="encoder", action="store_const", const="libsvtav1",
                     default=argparse.SUPPRESS,
                     help="AV1 (SVT-AV1)。同品質でHEVCの約半分になるが再生環境を選ぶ。"
                          "音声も既定でOpusになる")
    enc.add_argument("--h264", dest="encoder", action="store_const", const="libx264",
                     default=argparse.SUPPRESS,
                     help="H.264 (libx264)。最も互換性が高いが同品質だと最も大きい")
    content = p.add_mutually_exclusive_group()
    content.add_argument("--lecture", dest="content", action="store_const", const="lecture",
                         default=argparse.SUPPRESS,
                         help="スライド主体の講演動画向けの既定値にする"
                              f"（GOP {LECTURE_GOP_SECONDS:g}秒・強めのAQ・保守的なCRF）")
    content.add_argument("--general", dest="content", action="store_const", const="general",
                         default=argparse.SUPPRESS,
                         help="汎用素材（実写・アニメ）向けの既定値にする")
    p.add_argument("--apple", action="store_true",
                   help="写真.app / ファイル.app / QuickTime が開ける入れ物と音声に固定する"
                        "（MP4 + AAC）。映像コーデックは --hevc / --av1 / --h264 で選ぶ")
    p.add_argument("-s", "--size", type=parse_size, default=argparse.SUPPRESS, metavar="SIZE",
                   help=f"短辺の目標画素数。{' / '.join(SIZE_ALIASES)} か画素数を指定する。"
                        f"横長なら高さ、縦長なら幅に効く。拡大はしない"
                        f"（{SIZE_SOURCE} / 0=縮小しない。既定はこれで、端末実行なら聞く）")
    p.add_argument("-q", "--quality", choices=QUALITY_CHOICES, default=DEFAULT_QUALITY,
                   help="品質段階。コーデックと素材ごとのCRF表を引く")
    p.add_argument("-t", "--tune", default=None,
                   help="エンコーダのtune（animation / film / stillimage 等）。x264/x265のみ")
    p.add_argument("--crf", type=int, default=None,
                   help="CRFを直接指定して -q を上書きする（小さいほど高画質）。"
                        "目盛りはコーデックごとに異なる")
    p.add_argument("--preset", default=None,
                   help=f"エンコーダのpreset。"
                        f"既定: {' / '.join(f'{k}={v}' for k, v in DEFAULT_PRESET.items())}")
    p.add_argument("--gop-seconds", type=float, default=None,
                   help=f"キーフレーム間隔（秒）。既定: --lecture なら "
                        f"{LECTURE_GOP_SECONDS:g}、それ以外はエンコーダ任せ")
    p.add_argument("--audio-mode", choices=["auto", "prefer-copy", "mono", "stereo"], default="auto",
                   help=f"auto=非可逆{LOSSY_COPY_MAX_BITRATE // 1000}k以下ならコピー、可逆なら圧縮。"
                        "prefer-copy=可能な限りコピー（MP4で再生できないコーデックのみAAC化）")
    p.add_argument("--audio-codec", choices=["auto", "aac", "opus"], default="auto",
                   help="auto=--av1ならopus、それ以外はaac（--container mp4 指定時はaac）")
    p.add_argument("--container", choices=["auto", "mp4", "mkv", "webm"], default="auto",
                   help="出力コンテナ。auto=AV1+Opusならwebm、他のOpusならmkv、それ以外はmp4")
    p.add_argument("--audio-bitrate", type=int, default=None,
                   help="ステレオ再エンコード時のkbps（既定: aac 128 / opus 96）")
    p.add_argument("--mono-bitrate", type=int, default=None,
                   help="モノラル再エンコード時のkbps（既定: aac 128 / opus 64）")
    p.add_argument("-j", "--jobs", type=int, default=1, help="並列実行数")
    p.add_argument("--skip-existing", action="store_true", help="出力が既にあればスキップ")
    p.add_argument("--no-interactive", dest="interactive", action="store_false",
                   help="未指定のオプションを聞かず既定で実行する（端末以外では常にこの挙動）")
    p.add_argument("--no-progress", dest="progress", action="store_false",
                   help="進捗バーを出さない（端末以外・--verbose では常にこの挙動）")
    p.add_argument("--no-recursive", dest="recursive", action="store_false", help="サブディレクトリを辿らない")
    p.add_argument("--dry-run", action="store_true", help="コマンドを表示するだけで実行しない")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="ffmpegのコマンドラインと進捗を表示する（-j 2以上では出力が混ざる）")
    args = p.parse_args(argv)
    # --hevc/--av1 は default=SUPPRESS なので、未指定だと属性そのものが無い
    args.encoder = getattr(args, "encoder", None)
    args.content = getattr(args, "content", None)
    # 未指定(None)と「明示的に縮小しない」(0)を区別する。前者だけ対話で聞く。
    args.size = getattr(args, "size", None)
    # --crf を明示されたかは出力ファイル名にも出すので覚えておく
    args.crf_explicit = args.crf is not None

    # ffmpegの有無は対話で質問する前に確かめる。--help はここに到達しないので、
    # ffmpegが無い環境でも使い方だけは読める。
    missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing:
        p.exit(1, f"{' / '.join(missing)} が見つかりません\n")

    resolve_output_target(p, args)

    if args.tune and args.encoder is not None and args.encoder not in TUNE_ENCODERS:
        p.error(f"-t/--tune は {ENCODER_NAMES[args.encoder]} では効きません"
                "（x264/x265のみ。ffmpegのlibsvtav1は-tuneを黙って無視します）")

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
    # コンテナと音声コーデックを両方明示された場合は必ず矛盾するので、先に弾く。
    # 片方がautoで結果的に食い違う場合は container_audio_conflict が本数ごとに見る。
    if args.container == "mp4" and args.audio_codec == "opus":
        p.error("--container mp4 は --audio-codec opus と併用できません"
                "（AVFoundationにOpusデコーダがありません）")
    if args.container == "webm" and args.audio_codec == "aac":
        p.error("--container webm は --audio-codec aac と併用できません（WebMはOpus/Vorbisのみ）")
    if args.container == "webm" and args.encoder is not None and args.encoder not in WEBM_VIDEO_CODECS:
        p.error(f"--container webm は {args.encoder} を収容できません（--av1 と併用してください）")
    if args.container == "webm" and args.tune:
        p.error("--container webm は -t/--tune と併用できません"
                "（WebMに入るのはAV1/VP9で、-tune が効くのは x264/x265 だけです）")
    return args


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
            raise SystemExit(130)
        if not answer:
            return default
        chosen = to_int(answer)
        if chosen is not None and 1 <= chosen <= len(options):
            return options[chosen - 1][0]
        print(f"  1〜{len(options)} の番号で答えてください")


def resolve_options(args: argparse.Namespace) -> None:
    """未指定のオプションを、対話で聞くか既定値で埋める。

    端末から人が実行したときだけ質問する。パイプ・cron・--no-interactive では
    黙って既定（HEVC + MP4）に落ちるので、バッチ実行の挙動は変わらない。
    """
    interactive = args.interactive and sys.stdin.isatty() and sys.stdout.isatty()
    answered: list[str] = []

    if args.content is None:
        if interactive:
            args.content = prompt_choice("素材の種類を選んでください", CONTENT_CHOICES, DEFAULT_CONTENT)
            if args.content != DEFAULT_CONTENT:
                answered.append(f"--{args.content}")
        else:
            args.content = DEFAULT_CONTENT
    args.lecture = args.content == "lecture"

    if args.size is None:
        if interactive:
            chosen = prompt_choice("出力解像度を選んでください", SIZE_CHOICES, SIZE_SOURCE)
            args.size = parse_size(chosen)
            if chosen != SIZE_SOURCE:
                answered.append(f"-s {chosen}")
        else:
            args.size = 0

    if args.encoder is None:
        # 明示された --container / -t に合わないコーデックは選ばせない
        choices = [(value, label) for value, label in ENCODER_CHOICES
                   if (args.container != "webm" or value in WEBM_VIDEO_CODECS)
                   and (not args.tune or value in TUNE_ENCODERS)]
        fallback = DEFAULT_ENCODER if any(v == DEFAULT_ENCODER for v, _ in choices) else choices[0][0]
        if len(choices) == 1:
            args.encoder = choices[0][0]
        elif interactive:
            args.encoder = prompt_choice("映像コーデックを選んでください", choices, fallback)
            answered.append(f"--{ENCODER_NAMES[args.encoder]}")
        else:
            args.encoder = fallback

    # --apple が固定するのは入れ物と音声だけ。矛盾する指定があるときは聞かない。
    if interactive and not args.apple and args.audio_codec != "opus" and args.container in ("auto", "mp4"):
        args.apple = prompt_choice(
            "Apple機（写真.app / ファイル.app / QuickTime）で開ける形に固定しますか",
            [("no", "しない — 入れ物と音声は入力に合わせて決める"),
             ("yes", "する — MP4 + AAC に固定する")],
            "no",
        ) == "yes"
        if args.apple:
            answered.append("--apple")

    if args.apple:
        args.audio_codec, args.container = "aac", "mp4"
    elif args.container == "mp4" and args.audio_codec == "auto" and args.encoder == "libsvtav1":
        # MP4を指定されている。autoのままではOpusになるが、MP4のOpusはQuickTimeで
        # 鳴らないので、明示されたコンテナを優先してAACへ寄せる。
        args.audio_codec = "aac"

    if args.crf is None:
        args.crf = (LECTURE_CRF_MAP if args.lecture else CRF_MAP)[args.encoder][args.quality]
    if args.preset is None:
        args.preset = DEFAULT_PRESET[args.encoder]
    if args.gop_seconds is None:
        # 汎用素材ではエンコーダの既定に任せる（0で「指定しない」を表す）
        args.gop_seconds = LECTURE_GOP_SECONDS if args.lecture else 0.0
    if answered:
        print(f"（次回から {' '.join(answered)} を付けるか、--no-interactive で質問を省けます）")


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    resolve_options(args)
    roots = [p.resolve() for p in args.inputs]
    if args.outdir is not None:
        args.outdir = args.outdir.resolve()
    if args.output_file is not None:
        args.output_file = args.output_file.resolve()
    sources = collect_inputs(roots, args.outdir, args.recursive)
    if not sources:
        print("対象の動画が見つかりませんでした", file=sys.stderr)
        return 1

    jobs: list[tuple[MediaInfo, Path, AudioPlan]] = []
    skipped = 0   # 解析・組み合わせの都合で処理できなかった本数（終了コードに出す）

    if args.apple and args.encoder == "libsvtav1":
        # 通すが、再生できる機種が限られることは黙っていられない。
        print("注意: AV1はA17 Pro / M3世代以降のApple機でのみ再生できます"
              "（M1・M2世代では再生できません）")
    print(f"出力先: {args.output_file or args.outdir or roots[0].parent}"
          "（元ファイルは変更しません）")
    print(f"{len(sources)} 本を解析中…")
    for src in sources:
        try:
            info = probe(src)
        except (ProbeError, json.JSONDecodeError) as exc:
            print(f"  NG     {src.name}: {exc}", file=sys.stderr)
            skipped += 1
            continue

        # コンテナは音声の計画で決まる（Opusを使うならMKV）ので、先に立てる
        plan = build_audio_args(info, args)
        suffix = container_suffix(plan, args)
        conflict = container_audio_conflict(plan, info, suffix, args)
        if conflict:
            print(f"  NG     {src.name}: {conflict}", file=sys.stderr)
            skipped += 1
            continue
        dst = destination_for(info, roots, suffix, args)
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
        return 1 if skipped else 0

    results: list[Result] = []
    settings = [ENCODER_NAMES[args.encoder], f"CRF {args.crf}", f"preset {args.preset}"]
    if args.size:
        settings.append(f"短辺{args.size}px以下へ縮小")
    if args.tune:
        settings.append(f"tune {args.tune}")
    if args.lecture:
        settings.append("講演スライド向け")
    print(f"\n{len(jobs)} 本を {' / '.join(settings)} で圧縮します（並列 {args.jobs}）")
    progress = ProgressReporter(
        total_duration=sum(info.duration for info, _, _ in jobs),
        total_jobs=len(jobs),
        # ffmpegの進捗をそのまま流す--verboseや、行を書き換えられない端末以外では出さない
        enabled=args.progress and not args.verbose and not args.dry_run and sys.stdout.isatty(),
    )
    with ThreadPoolExecutor(max_workers=max(args.jobs, 1)) as pool:
        futures = {pool.submit(encode, info, dst, plan, args, progress): info
                   for info, dst, plan in jobs}
        for done, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            results.append(result)
            if not result.ok:
                progress.report(f"[{done}/{len(jobs)}] NG {result.src.name}: {result.message}",
                                error=True)
            elif not args.dry_run:
                ratio = result.dst_size / result.src_size if result.src_size else 0
                progress.report(f"[{done}/{len(jobs)}] {result.src.name}: "
                                f"{human(result.src_size)} → {human(result.dst_size)} "
                                f"({ratio:.0%}) / {result.message}")
    progress.close()

    if args.dry_run:
        return 1 if skipped else 0

    ok = [r for r in results if r.ok]
    src_total = sum(r.src_size for r in ok)
    dst_total = sum(r.dst_size for r in ok)
    print(f"\n完了 {len(ok)}/{len(results)} 本")
    if src_total:
        print(f"合計 {human(src_total)} → {human(dst_total)} "
              f"({dst_total / src_total:.0%}, {human(src_total - dst_total)} 削減)")
    return 0 if len(ok) == len(results) and not skipped else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
