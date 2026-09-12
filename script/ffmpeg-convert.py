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

出力が既にある場合は既定でスキップする。設定を変えて作り直したいときだけ --overwrite。

--replace: 変換結果で元ファイルを置き換える（-o とは併用できない）。
  ffmpeg-convert.py . --replace                  ディレクトリ丸ごと、その場で置き換える
元ファイルは消さずゴミ箱へ移すので取り戻せる。出力が元より大きくなった本数は
置き換えず元を残す（再圧縮して太るなら意味がないため）。

--lecture: スライド主体のWeb講演動画向けモード。
  - 画面のほとんどが静止したスライド（動きが極端に少ない）
  - 細かい文字が多く、解像度と文字の可読性は落とせない
  - 音声はナレーションのみ
こうした素材に合わせて、長いGOP・強めのAQ・保守的なCRFへ既定値を差し替える。

端末から実行して素材・解像度・Apple互換・映像コーデック・画質・音声コーデックを省いた
場合は、どれにするかを対話で聞く。パイプ・cron・--no-interactive では何も聞かず既定
（汎用素材 + 元の解像度 + HEVC + normal + MP4）で走るので、バッチ実行は変わらない。
"""

from __future__ import annotations

import argparse
import colorsys
import functools
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
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
# 対話モードで提示する品質段階（値, 説明）。CRFの実値はコーデックと素材で変わるので、
# 説明には書かず、質問する時点で決まっているCRF表から引いて添える。
QUALITY_DESCRIPTIONS = [
    ("low", "low — 内容が分かれば良い。容量を最優先"),
    ("portable", "portable — 持ち歩き・共有用。容量を抑える"),
    ("normal", "normal — 一般的な視聴に十分"),
    ("high", "high — 元の見た目をほぼ保つ"),
    ("veryhigh", "veryhigh — 元と見分けがつきにくい。容量は大きい"),
]
QUALITY_CHOICES = [value for value, _ in QUALITY_DESCRIPTIONS]
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

# 対話モードで提示する音声コーデック（値, 説明）。先頭が既定。
# ここで選ぶのは「再エンコードするときに何にするか」で、コピーで済むかは別の判断。
AUDIO_CODEC_CHOICES = [
    ("auto", "映像に合わせる — HEVC / H.264 ならAAC、AV1ならOpus"),
    ("aac", "AAC — 互換性優先。どの機種でも鳴る。コピーで済む音声はコピーする"),
    ("opus", "Opus — 容量優先。必ず再エンコードし、入れ物はMKV/WebMになる。Apple機では鳴らない"),
]
DEFAULT_AUDIO_CODEC = AUDIO_CODEC_CHOICES[0][0]

# -t/--tune が効くエンコーダ。ffmpegのlibsvtav1ラッパーは tune オプションを
# 公開していないため、-tune を渡してもエラーにならず黙って無視される。
# 「指定したのに効かない」を避けるため、AV1では -t をエラーで返す。
# （SVT-AV1自身の tune=0/1/2 は -svtav1-params tune=N でしか触れない別物）
TUNE_ENCODERS = frozenset({"libx264", "libx265"})

# Opusは音声において AAC-LC の1.5〜2倍効率が良いので、同品質をより少ないビットで買える。
# 64k mono ≒ 128k AAC mono。
DEFAULT_AUDIO_BITRATE = {"aac": {1: 128, 2: 128}, "libopus": {1: 64, 2: 96}}

# 結果行でファイル名に割り当てる表示幅の上限。これを超える名前は欄からはみ出す。
RESULT_NAME_MAX_WIDTH = 40

# 進捗バーのアニメーション。ffmpegの -progress は0.5秒に1回しか来ないので、
# 滑らかに動かすには独立したティックが要る。15fpsあれば波の流れは十分見える。
PROGRESS_FPS = 15.0

BAR_FILLED, BAR_EMPTY = "█", "░"
BAR_EMPTY_RGB = (80, 80, 80)

# 速度帯 → バーの色（下限, RGB）。実時間に対する倍率で、1.0が等速。
# 「赤＝待たされる / 緑＝等速より速い / 青＝快調」が一目で分かるようにする。
SPEED_COLORS = [
    (0.0, (215, 60, 50)),     # 赤 —— 等速の1/3未満。かなり遅い
    (0.3, (220, 130, 30)),    # オレンジ
    (1.0, (70, 190, 90)),     # 緑 —— 実時間より速い
    (3.0, (70, 145, 240)),    # 青
]
# 再圧縮して元より太った本を目立たせる色。速度帯のオレンジと同じ系統。
GREW_RGB = (220, 130, 30)

# これ以上はレインボー。色相がバー内を流れる。
RAINBOW_SPEED = 7.0
RAINBOW_SECONDS = 2.0     # 色相が1周する秒数
RAINBOW_TURNS = 1.0       # バーの端から端で色相が何周するか

# 単色帯では明度を波で揺らして光沢が流れているように見せる。
BAR_WAVE_SECONDS = 1.6    # 波が左から右へ1周する秒数
BAR_WAVES = 1.5           # バー内に見える波の数
BAR_WAVE_FLOOR = 0.55     # 波の谷での明度（1.0が元の色）

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

# x264とx265はエンコーダ固有パラメータを専用フラグで受ける。SVT-AV1は持たない。
PARAMS_FLAG = {"libx264": "-x264-params", "libx265": "-x265-params"}

# WebMはMatroskaのサブセットで、収容できるコーデックが限られる。
WEBM_VIDEO_CODECS = frozenset({"libsvtav1", "libvpx-vp9", "libvpx"})
WEBM_AUDIO_CODECS = frozenset({"libopus", "libvorbis"})
WEBM_AUDIO_CODEC_NAMES = frozenset(ENCODER_CODEC_NAME[enc] for enc in WEBM_AUDIO_CODECS)

# -o をファイル名として受け取れる拡張子。ここから出力コンテナも決まる。
CONTAINER_SUFFIXES = {".mp4": "mp4", ".mkv": "mkv", ".webm": "webm"}


class ProbeError(RuntimeError):
    pass


def crf_table(lecture: bool, encoder: str) -> dict[str, int]:
    """そのコーデック・素材での 品質段階 → CRF の対応表。"""
    return (LECTURE_CRF_MAP if lecture else CRF_MAP)[encoder]


@dataclass(frozen=True)
class Config:
    """解決済みの実行設定。コマンドライン引数と対話の答えを1つにまとめたもの。

    argparse.Namespace と違い、ここに来る時点で全項目が確定している（「未指定」を
    表す None は残らない）ので、受け取る側は既定値の埋め直しを気にしなくてよい。
    """

    # --- 入力と出力先 ---
    roots: tuple[Path, ...]          # 走査の起点（絶対パス）
    outdir: Path | None              # 出力先ディレクトリ。Noneは「入力と同じ場所」
    output_file: Path | None         # 出力パスが1つに確定していればそのPath
    single_file: bool                # 単発ファイルの変換か（出力名の付け方が変わる）
    recursive: bool
    overwrite: bool
    replace: bool

    # --- 映像 ---
    encoder: str
    size: int                        # 短辺の目標画素数。0は縮小しない
    quality: str
    crf: int
    crf_explicit: bool               # --crf を明示されたか（出力ファイル名に出す）
    preset: str
    tune: str | None
    gop_seconds: float               # 0はエンコーダ任せ
    lecture: bool

    # --- 音声と入れ物 ---
    apple: bool
    container: str
    audio_mode: str
    audio_codec: str
    audio_bitrate: int | None
    mono_bitrate: int | None

    # --- 実行のしかた ---
    jobs: int
    dry_run: bool
    verbose: bool
    progress: bool

    @property
    def mp4_audio_codecs(self) -> frozenset[str]:
        """MP4に入れてそのまま鳴ると認める音声コーデック。--apple ならより厳しく絞る。"""
        return APPLE_SAFE_AUDIO_CODECS if self.apple else MP4_SAFE_AUDIO_CODECS

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


@dataclass(frozen=True)
class Job:
    """1本分の変換内容。解析の時点で確定し、そのままエンコードへ渡る。"""

    info: MediaInfo
    dst: Path
    plan: AudioPlan


@dataclass
class Result:
    src: Path
    dst: Path
    ok: bool
    message: str
    src_size: int = 0
    dst_size: int = 0
    # --replace で「出力の方が大きいので置き換えなかった」印。失敗ではないが成果でもない
    kept: bool = False


# ---------------------------------------------------------------------------
# ffprobe による解析
# ---------------------------------------------------------------------------


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


def to_int(value: object) -> int | None:
    try:
        return int(value)   # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


@functools.lru_cache(maxsize=None)
def measure_channel_difference(path: Path) -> float:
    """L-R の最大音量を dBFS で返す。無音（＝左右同一）なら大きな負の値。

    音声を実際にデコードするので安くはない。再エンコードすると決まった後に
    「ついでにモノへまとめられるか」を判断するためだけに呼ぶこと。
    コピーで済む入力に対しては呼ばれない。

    -vn は必須。filter_complex が [0:a] しか使っていなくても、-map が無いと
    ffmpegの自動ストリーム選択が映像も拾い、null muxerへ向けて律儀に全フレームを
    デコードしてしまう（1080p・180秒で実測5秒）。音量の測定値は -vn の有無で変わらない。
    """
    filt = (
        "[0:a]channelsplit=channel_layout=stereo[l][r];"
        "[l][r]amerge=inputs=2,aeval=val(0)-val(1):c=mono,volumedetect"
    )
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-t", str(AUDIO_PROBE_SECONDS), "-i", str(path),
         "-vn", "-filter_complex", filt, "-f", "null", "-"],
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


def probe_duration(path: Path) -> float:
    data = run_json([
        "ffprobe", "-v", "error", "-print_format", "json", "-show_format", str(path),
    ])
    return float(data.get("format", {}).get("duration") or 0.0)


# ---------------------------------------------------------------------------
# 映像の組み立て
# ---------------------------------------------------------------------------


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


def build_video_args(info: MediaInfo, cfg: Config) -> list[str]:
    out = ["-c:v", cfg.encoder, "-preset", cfg.preset, "-crf", str(cfg.crf)]

    # AV1では -tune が黙って無視されるため parse_args で弾いてある。
    # ここに来る cfg.tune は x264/x265 に渡る値だけ。
    if cfg.tune:
        out += ["-tune", cfg.tune]

    if cfg.encoder == "libsvtav1":
        # 同品質ならHEVCの半分程度で済むが、再生環境を選ぶ。
        # screen content mode (scm=1) は測定上ほぼ無効果だったので使わない
        # ―― 日本語のアンチエイリアス文字だけでパレットモードの色数上限を超えるため。
        if cfg.gop_seconds:
            out += ["-g", str(keyint_frames(info, cfg.gop_seconds))]
    else:
        params: list[str] = []
        if cfg.gop_seconds:
            params += [
                f"keyint={keyint_frames(info, cfg.gop_seconds)}",
                f"min-keyint={keyint_frames(info, 1.0)}",
            ]
        if cfg.lecture:
            # 平坦な背景上の細い文字にビットを回す
            params += ["aq-mode=3", "rc-lookahead=60", "bframes=6"]
            if cfg.encoder == "libx265":
                # x264のpsy-rdは2値指定で既定が既に1.0なので、x265だけ明示する
                params.append("psy-rd=1.0")
        if cfg.encoder == "libx265":
            params.append("log-level=error")   # x265は既定で冗長
        if params:
            out += [PARAMS_FLAG[cfg.encoder], ":".join(params)]

    scale = scale_filter(info, cfg.size)
    if scale:
        out += ["-vf", scale]

    out += ["-pix_fmt", "yuv420p"]
    if cfg.encoder == "libx265":
        # QuickTime等がHEVCと認識するためのブランド。AV1(av01)/H.264には不要。
        out += ["-tag:v", "hvc1"]
    return out


# ---------------------------------------------------------------------------
# 音声とコンテナの組み立て
# ---------------------------------------------------------------------------


def container_suffix(plan: AudioPlan, cfg: Config) -> str:
    """出力コンテナの拡張子。映像・音声コーデックの組み合わせで決まる。"""
    if cfg.container != "auto":
        return f".{cfg.container}"
    if not plan.needs_matroska:
        return ".mp4"
    # Opusを使う場合。AV1と組めばWebMに収まり、こちらの方が対応環境が広い。
    # HEVC+OpusはWebMに入らないのでMKVにする。
    if cfg.encoder in WEBM_VIDEO_CODECS and plan.codec in WEBM_AUDIO_CODECS:
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
                             cfg: Config) -> str | None:
    """コンテナに入らない音声の組み合わせを、ffmpegを起動する前に見つける。

    --container を明示するとauto時の安全な組み合わせから外れることがある。
    そのままffmpegに渡すと "Nothing was written into output file" のような
    原因の分からないエラーで落ちるので、理由を添えて先に弾く。
    収容制限を持たないコンテナ（.mkv）は常に通す。
    """
    codec = output_audio_codec(plan, info)
    if codec is None:
        return None
    allowed = {".mp4": cfg.mp4_audio_codecs, ".webm": WEBM_AUDIO_CODEC_NAMES}.get(suffix)
    if allowed is None or codec in allowed:
        return None
    return (f"{suffix.lstrip('.')} に {codec} 音声は入れられません"
            f"（--container / --audio-codec / --audio-mode を見直してください）")


def resolve_audio_codec(cfg: Config) -> str:
    """再エンコードする場合に使う音声コーデック。

    AV1を選んだ場合はアーカイブ用途とみなし、対になるOpusを既定にする。
    映像が半分になると音声が容量の約半分を占めるようになるため。
    """
    if cfg.audio_codec == "opus":
        return "libopus"
    if cfg.audio_codec == "aac":
        return "aac"
    return "libopus" if cfg.encoder == "libsvtav1" else "aac"


def build_audio_args(info: MediaInfo, cfg: Config) -> AudioPlan:
    audio = info.audio
    if audio is None:
        return AudioPlan(["-an"], "音声なし")

    codec = (audio.codec or "").lower()
    mp4_safe = codec in cfg.mp4_audio_codecs
    unsafe_reason = "はApple環境で確実に鳴らない" if cfg.apple else "はMP4で再生できない"
    kbps = audio.bitrate // 1000 if audio.bitrate else None
    out_codec = resolve_audio_codec(cfg)

    def encode(channels: int, reason: str) -> AudioPlan:
        override = cfg.mono_bitrate if channels == 1 else cfg.audio_bitrate
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

    if cfg.audio_mode == "mono":
        return encode(1, "指定")
    if cfg.audio_mode == "stereo":
        return encode(min(audio.channels, 2), "指定")
    if cfg.audio_mode == "prefer-copy":
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


# ---------------------------------------------------------------------------
# 表示の整形
# ---------------------------------------------------------------------------

SIZE_UNITS = ("B", "KB", "MB", "GB", "TB")

# サイズの数字に割り当てる桁数。単位は大きい方の値に合わせるので、どの値も1024未満に
# 収まり、"1023.9" の6桁が上限になる。
SIZE_NUMBER_WIDTH = 6


def size_unit(n: float) -> str:
    """そのバイト数を読みやすく表せる単位。"""
    for unit in SIZE_UNITS[:-1]:
        if abs(n) < 1024:
            return unit
        n /= 1024
    return SIZE_UNITS[-1]


def common_unit(*sizes: float) -> str:
    """複数のサイズを並べて見せるときに共通で使う単位。

    大きい方に合わせる。小さい方に合わせると、比が開いたときに大きい側が
    「26774.3 KB」のように桁あふれして列が崩れるため。小さい側の桁は human() が
    小数を増やして残す。
    """
    return size_unit(max(sizes))


def human(n: float, unit: str | None = None, align: bool = False) -> str:
    """バイト数を読める単位にする。

    unitを渡すとその単位で表す。変換前後を並べるときに単位が食い違うと
    「1.0 MB → 194.0 KB」のように増えたと錯覚するので、左右で揃えるために使う
    （揃える単位は common_unit で決める）。
    align=True では数字を右詰め・単位を左詰めにして幅を固定し、結果行のように縦に
    並べたとき桁が揃うようにする。
    """
    unit = unit or size_unit(n)
    value = n / 1024 ** SIZE_UNITS.index(unit)
    # 1未満は桁数を増やす。大きい方に単位を合わせると小さい方が「0.9 MB」のように
    # 潰れるので、有効数字を2桁保つ。どちらも幅は同じなので列は揃ったまま
    decimals = 2 if 0 < abs(value) < 1 else 1
    return (f"{value:{SIZE_NUMBER_WIDTH}.{decimals}f} {unit:<2}" if align
            else f"{value:.{decimals}f} {unit}")


def size_change(src_size: int, dst_size: int, show_saved: bool = False) -> str:
    """「  1.3 MB →  800.0 KB ( 60%)」の形。単位は左右で揃える。

    結果行と合計行で同じ欄・同じ幅を使うため、整形はここ1箇所にまとめる。
    show_saved=True では括弧の中に増減量も添える（合計行用）。

    再圧縮して元より太った場合は「増加」と書き、括弧ごとオレンジにする。
    負の削減量（-113.3 MB 削減）は読み取りに一拍かかるうえ、見逃しやすいため。
    """
    unit = common_unit(src_size, dst_size)
    ratio = dst_size / src_size if src_size else 0
    delta = src_size - dst_size
    note = ""
    if show_saved:
        note = (f", {human(delta, unit)} 削減" if delta >= 0
                else f", {human(-delta, unit)} 増加")
    change = f"({ratio:>4.0%}{note})"
    if delta < 0:
        change = paint(change, GREW_RGB)
    return (f"{human(src_size, unit, align=True)} → {human(dst_size, unit, align=True)} "
            f"{change}")


# SGR（色指定）。表示幅を持たないので、幅を数えるときは取り除く。
SGR_PATTERN = re.compile(r"\x1b\[[0-9;]*m")
SGR_RESET = "\033[0m"


@functools.cache
def use_color() -> bool:
    """24bit色を出してよい端末か。

    サブパラメータのコロン区切り（38:2::r:g:b）はTerminal.appが解釈しないので、
    綴りは必ずセミコロン区切りにすること。判定は COLORTERM のみを見る保守的な
    もので、分からなければ色を使わず今までどおりの見た目に落とす。
    パイプやファイルへ流すときは、色が中身に混ざらないよう必ず落とす。
    """
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return False
    return os.environ.get("COLORTERM", "").lower() in ("truecolor", "24bit")


def sgr(rgb: tuple[int, int, int]) -> str:
    return f"\033[38;2;{rgb[0]};{rgb[1]};{rgb[2]}m"


def paint(text: str, rgb: tuple[int, int, int]) -> str:
    """色が使える端末なら着色する。使えないならそのまま返す。"""
    return f"{sgr(rgb)}{text}{SGR_RESET}" if use_color() else text


def band_color(speed: float) -> tuple[int, int, int]:
    """その速度を表す色。波の変調は載せない（数字に添える用）。"""
    if speed >= RAINBOW_SPEED:
        return hue_rgb(0.0)
    return next(rgb for limit, rgb in reversed(SPEED_COLORS) if speed >= limit)


def hue_rgb(hue: float) -> tuple[int, int, int]:
    r, g, b = colorsys.hsv_to_rgb(hue % 1.0, 0.85, 1.0)
    return (round(r * 255), round(g * 255), round(b * 255))


def bar_cell_color(speed: float, position: float, phase: float) -> tuple[int, int, int]:
    """バー1マスの色。position はバー内の位置(0..1)、phase は経過秒。

    速度が上がるほど帯の色が変わり、最上位の帯ではレインボーが流れる。
    それ以外の帯では帯色の明度を波で揺らして、同じように流れて見せる。
    """
    if speed >= RAINBOW_SPEED:
        return hue_rgb(position * RAINBOW_TURNS - phase / RAINBOW_SECONDS)
    wave = math.sin(2 * math.pi * (position * BAR_WAVES - phase / BAR_WAVE_SECONDS))
    level = BAR_WAVE_FLOOR + (1 - BAR_WAVE_FLOOR) * (wave + 1) / 2
    return tuple(min(255, round(c * level)) for c in band_color(speed))   # type: ignore[return-value]


def char_width(ch: str) -> int:
    """端末上での1文字の表示幅。全角（W/F）は2桁。"""
    return 2 if unicodedata.east_asian_width(ch) in "WF" else 1


def display_width(text: str) -> int:
    """端末上での表示幅。日本語などの全角文字は2桁として数える。

    色指定（SGR）は桁を食わないので、数える前に取り除く。
    """
    return sum(char_width(ch) for ch in SGR_PATTERN.sub("", text))


def pad_display(text: str, width: int) -> str:
    """表示幅が width になるよう右を空白で埋める。既に超えていればそのまま返す。"""
    return text + " " * max(width - display_width(text), 0)


def truncate_display(text: str, limit: int) -> str:
    """表示幅が limit を超えないよう末尾を落とす。進捗行の折り返しを防ぐため。

    色指定（SGR）は桁を食わないのでそのまま通す。色の途中で切れても端末に色が
    残らないよう、切り詰めたときはリセットを足す。
    """
    if display_width(text) <= limit:
        return text
    kept: list[str] = []
    width, index = 0, 0
    while index < len(text):
        match = SGR_PATTERN.match(text, index)
        if match:
            kept.append(match.group())
            index = match.end()
            continue
        width += char_width(text[index])
        if width > limit - 1:
            break
        kept.append(text[index])
        index += 1
    tail = SGR_RESET if SGR_PATTERN.search(text) else ""
    return "".join(kept) + "…" + tail


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


@dataclass(frozen=True)
class ResultLayout:
    """結果行の桁を揃えるための幅。

    「[ 1/11] name: 」までを固定幅にすると、後ろに続くサイズが縦に並ぶ。
    名前の欄には上限を設けて、極端に長い1本に全部を引きずられないようにする
    （超えた行だけがはみ出し、他の行は揃ったまま）。
    """

    total: int
    counter_width: int
    prefix_width: int

    @classmethod
    def for_jobs(cls, jobs: list[Job]) -> ResultLayout:
        counter_width = len(str(len(jobs)))
        name_width = min(max(display_width(job.info.path.name) for job in jobs),
                         RESULT_NAME_MAX_WIDTH)
        prefix_width = display_width(f"[{0:>{counter_width}}/{len(jobs)}] ") + name_width + 1
        return cls(len(jobs), counter_width, prefix_width)

    def counter(self, n: int) -> str:
        """「[ 3/31]」。結果行と進捗バーで同じ幅になるよう、整形はここだけで行う。"""
        return f"[{n:>{self.counter_width}}/{self.total}]"

    def done_counter(self, n: int) -> str:
        """「完了  3/31」。特定の1本を指せないとき（並行実行中）に使う。"""
        return f"完了 {n:>{self.counter_width}}/{self.total}"

    def prefix(self, done: int, name: str) -> str:
        return self.label(f"{self.counter(done)} {name}:")

    def label(self, text: str) -> str:
        """結果行と同じ欄に置く見出し（合計行など）。"""
        return pad_display(text, self.prefix_width)


class ProgressReporter:
    """エンコード中の進捗を1行にまとめて表示する。

    総尺は解析時に分かっているので、全体に対する処理済み秒数で進捗率を出せる。
    -j で並列にしても行が混ざらないよう、本数ごとではなく全体を1行だけ書き換える。
    端末以外（パイプ・cron）・--verbose・--dry-run では何もしないので、
    ログの見た目は今までどおり。
    """

    BAR_WIDTH = 20

    def __init__(self, total_duration: float, layout: ResultLayout, enabled: bool,
                 sequential: bool) -> None:
        self.total_duration = total_duration
        self.layout = layout
        self.enabled = enabled
        self.sequential = sequential
        self.color = enabled and use_color()
        self.lock = threading.Lock()
        self.running: dict[Path, tuple[float, float]] = {}   # src -> (処理済み秒, 速度)
        self.done_duration = 0.0
        self.done_jobs = 0
        self.started = time.monotonic()
        # 本と本の合間は走っているものが無く速度が0になる。バーの色がそのたびに
        # 最低速の帯（赤）へ落ちるのを避けるため、直近の速さを覚えておく。
        self.last_per_file = 0.0
        self._stop = threading.Event()
        self._ticker: threading.Thread | None = None

    @classmethod
    def for_jobs(cls, jobs: list[Job], cfg: Config, layout: ResultLayout) -> ProgressReporter:
        return cls(
            total_duration=sum(job.info.duration for job in jobs),
            layout=layout,
            sequential=cfg.jobs <= 1,
            # ffmpegの進捗をそのまま流す--verboseや、行を書き換えられない端末以外では出さない
            enabled=cfg.progress and not cfg.verbose and not cfg.dry_run and sys.stdout.isatty(),
        )

    def __enter__(self) -> ProgressReporter:
        """アニメーション用の再描画スレッドを回し始める。

        ffmpegの -progress は0.5秒に1回しか来ないので、それだけを描画の契機に
        すると波が飛び飛びになる。色を使わないときは動かす意味がないので回さない。
        """
        if self.color:
            self._ticker = threading.Thread(target=self._tick, daemon=True)
            self._ticker.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _tick(self) -> None:
        while not self._stop.wait(1.0 / PROGRESS_FPS):
            with self.lock:
                self._render()

    def update(self, src: Path, out_time: float, speed: float) -> None:
        """ffmpegから届いた1本分の進捗を反映する。"""
        with self.lock:
            self.running[src] = (out_time, speed)
            self._render()

    def finish(self, src: Path, duration: float) -> None:
        """1本終わった分を完了側に移す。

        本数は数えない。エンコードを終えたワーカーがここを通ってから、本体が結果行を
        出すまでには間があり、その間にティックが走ると結果行より先にバーの番号が
        進んでしまうため（実際 [11/12] のバーの後に [10/12] の結果行が出ていた）。
        """
        with self.lock:
            self.running.pop(src, None)
            self.done_duration += duration

    def report(self, line: str, error: bool = False) -> None:
        """結果行を1本出す。進捗行を潰さないように、消す→出す→描き直す。

        呼び出しは1本につき1回なので、ここで本数を数える。こうするとバーの番号は
        「最後に出した結果行の次」に必ず一致し、追い越しが起きない。
        """
        with self.lock:
            self.done_jobs += 1
            self._erase()
            print(line, file=sys.stderr if error else sys.stdout, flush=True)
            self._render()

    def close(self) -> None:
        """進捗行を消して、以降は普通の出力に戻す。"""
        # 先にティックを止める。ロックを持ったまま join すると、_render 待ちの
        # スレッドと相討ちになって固まる。
        self._stop.set()
        if self._ticker is not None:
            self._ticker.join(timeout=1.0)
            self._ticker = None
        with self.lock:
            self._erase()
            self.enabled = False

    def _paint(self, text: str, rgb: tuple[int, int, int]) -> str:
        return paint(text, rgb) if self.color else text

    def _paint_bar(self, filled: int, speed: float, phase: float) -> str:
        """バーを組み立てる。色が使えるなら、速度に応じた光沢を流す。"""
        if not self.color:
            return f"[{BAR_FILLED * filled}{BAR_EMPTY * (self.BAR_WIDTH - filled)}]"
        cells: list[str] = []
        last: tuple[int, int, int] | None = None
        for index in range(self.BAR_WIDTH):
            if index < filled:
                position = index / max(self.BAR_WIDTH - 1, 1)
                rgb, char = bar_cell_color(speed, position, phase), BAR_FILLED
            else:
                rgb, char = BAR_EMPTY_RGB, BAR_EMPTY
            if rgb != last:   # 同じ色が続くならSGRを繰り返さない
                cells.append(sgr(rgb))
                last = rgb
            cells.append(char)
        return f"[{''.join(cells)}{SGR_RESET}]"

    def _erase(self) -> None:
        if self.enabled:
            print("\r\033[K", end="", flush=True)

    def _render(self) -> None:
        if not self.enabled:
            return
        processed = self.done_duration + sum(t for t, _ in self.running.values())
        running = len(self.running)
        # 合算スループット。残り時間はこれで割る（全体が何倍速で進んでいるか）
        speed = sum(s for _, s in self.running.values())
        # 1本あたりの速さ。色はこちらで決める。合算のままだと -j 3 で 6x×3=18x となり、
        # 並行数を上げただけで最上位帯へ張り付いて色が情報を持たなくなるため。
        per_file = speed / running if running else 0.0
        if per_file > 0:
            self.last_per_file = per_file
        phase = time.monotonic() - self.started

        # 逐次実行では、いま処理している本が何本目かを出す。行末にファイル名が並ぶので、
        # 番号もそのファイルを指していないと「f2.mov が1本目」と読めてしまう。
        # この番号は、その本が終わったときに出る結果行の番号と必ず一致する。
        # 本と本の合間（走っているものが無い）も次の1本の番号のまま据え置く。完了本数へ
        # 戻すと、合間だけ表示幅が変わって行が横にずれるため。
        #
        # 並行実行では先読みできない。結果行の番号は完了順に振られるので、走っている
        # 1本が次に終わるとは限らず、先に出した番号が別のファイルに付いてしまう。
        # 特定の1本を指せない以上、完了本数だと分かる書き方にする。
        parts = [self.layout.counter(min(self.done_jobs + 1, self.layout.total))
                 if self.sequential else self.layout.done_counter(self.done_jobs)]
        if self.total_duration > 0:
            ratio = min(processed / self.total_duration, 1.0)
            filled = round(ratio * self.BAR_WIDTH)
            parts.append(f"{ratio:4.0%} "
                         f"{self._paint_bar(filled, per_file or self.last_per_file, phase)}")
            parts.append(f"{clock(processed)}/{clock(self.total_duration)}")
            if speed > 0:
                parts.append(f"残り {clock((self.total_duration - processed) / speed)}")
        else:
            parts.append(f"{clock(processed)} 処理済み")
        if speed > 0:
            # 並行中は「1本あたり / 本数」で出す。色と同じ数字を見せないと、
            # なぜその色なのかが分からなくなる。合算値は残り時間に現れている。
            text = f"{per_file:.3g}x / {running}" if running > 1 else f"{speed:.3g}x"
            # 数字にも帯の色を乗せて、バーの色が何を表しているのかを結び付ける
            parts.append(self._paint(text, band_color(per_file)))
        if running == 1:
            parts.append(next(iter(self.running)).name)

        columns = shutil.get_terminal_size(fallback=(80, 24)).columns
        print("\r\033[K" + truncate_display(" ".join(parts), columns - 1), end="", flush=True)


# ---------------------------------------------------------------------------
# エンコードの実行
# ---------------------------------------------------------------------------


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


def trash_directory(path: Path) -> Path:
    """path と同じボリュームにあるゴミ箱。無ければ作る。

    ボリュームを跨ぐ移動は実体のコピーになり、動画では一瞬で終わらない。
    起動ボリュームなら ~/.Trash、外付けならそのボリュームの .Trashes/<uid>。
    """
    device = path.stat().st_dev
    home = Path.home()
    if device == home.stat().st_dev:
        trash = home / ".Trash"
    else:
        volume = path.parent
        while volume.parent != volume and volume.parent.stat().st_dev == device:
            volume = volume.parent
        trash = volume / ".Trashes" / str(os.getuid())
    trash.mkdir(parents=True, exist_ok=True)
    return trash


def move_to_trash(path: Path) -> None:
    """ファイルをゴミ箱へ移す。移せなければ OSError。

    unlinkではなくゴミ箱にするのは、--replace が消すのが変換前の原本だから。
    Finder経由（osascript）なら「戻す」も効くが、ssh・launchdではFinderに
    繋がらず必ず失敗する。ゴミ箱から取り出せれば足りるので、mv相当で済ませる。
    """
    trash = trash_directory(path)
    destination = trash / path.name
    if destination.exists():
        # 同名が既にゴミ箱にある。日時を足して、先に捨てた方を上書きしない
        destination = trash / f"{path.stem} {datetime.now():%Y-%m-%d-%H-%M-%S}{path.suffix}"
    path.rename(destination)


def build_encode_command(info: MediaInfo, tmp: Path, plan: AudioPlan, cfg: Config,
                         with_progress: bool) -> list[str]:
    """1本分のffmpegコマンドライン。出力は書きかけの一時ファイル。"""
    cmd = [
        "ffmpeg", "-y", "-nostdin",
        *(["-v", "info", "-stats"] if cfg.verbose else ["-v", "error", "-nostats"]),
        *(["-progress", "pipe:1"] if with_progress else []),
        "-i", str(info.path),
        "-map", "0:v:0",
        *build_video_args(info, cfg),
    ]
    if info.audio is not None:
        cmd += ["-map", "0:a:0", *plan.args]
    else:
        cmd += ["-an"]
    if tmp.suffix.lower() == ".mp4":
        cmd += ["-movflags", "+faststart"]
    cmd += [str(tmp)]
    return cmd


def run_encoder(cmd: list[str], src: Path, cfg: Config,
                progress: ProgressReporter) -> tuple[int, str]:
    """ffmpegを走らせて (終了コード, stderr) を返す。受け取り方は表示方法で変わる。"""
    if cfg.verbose:
        # ffmpeg自身の進捗をそのまま流したいので捕捉しない
        return subprocess.run(cmd).returncode, ""
    if progress.enabled:
        return run_with_progress(cmd, src, progress)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stderr


def verify_output(tmp: Path, expected_duration: float) -> str | None:
    """尺が合っているかで壊れた出力を弾く。問題なければNone、あれば理由を返す。"""
    try:
        out_duration = probe_duration(tmp)
    except ProbeError as exc:
        return f"出力を検証できません: {exc}"
    if expected_duration > 0 and abs(out_duration - expected_duration) > 1.0:
        return f"尺が不一致 ({out_duration:.1f}s vs {expected_duration:.1f}s)"
    return None


def prepare_replace(info: MediaInfo, tmp: Path, dst: Path) -> Result | None:
    """--replace の下準備。置き換えずに終えるならその Result、進めてよければ None。"""
    src = info.path
    new_size = tmp.stat().st_size
    # 太るなら置き換える理由がない。容量は増え画質は落ちるので、原本の方が上
    if new_size >= info.size:
        tmp.unlink(missing_ok=True)
        unit = common_unit(info.size, new_size)
        return Result(src, dst, True,
                      f"元より大きいので置き換えません"
                      f"（{human(new_size, unit)} ≥ {human(info.size, unit)}）",
                      info.size, info.size, kept=True)
    # ゴミ箱へ移すのが先。拡張子が変わらず dst と src が同じパスのとき、
    # 後回しにすると呼び出し元の replace が原本を上書きして消してしまう
    try:
        move_to_trash(src)
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        return Result(src, dst, False, f"元ファイルをゴミ箱へ移せません: {exc}", info.size, 0)
    return None


def encode(job: Job, cfg: Config, progress: ProgressReporter) -> Result:
    info, dst = job.info, job.dst
    src = info.path
    tmp = dst.with_name(dst.name + ".part" + dst.suffix)
    cmd = build_encode_command(info, tmp, job.plan, cfg, progress.enabled)

    if cfg.dry_run:
        destination = f"\n          → {dst.name}（元はゴミ箱へ）" if cfg.replace else ""
        print(f"[dry-run] {src.name}\n          audio: {job.plan.note}{destination}"
              f"\n          {shlex.join(cmd)}")
        return Result(src, dst, True, "dry-run", info.size, 0)

    dst.parent.mkdir(parents=True, exist_ok=True)
    if cfg.verbose:
        print(f"--- {src.name}\n    audio: {job.plan.note}\n    {shlex.join(cmd)}", flush=True)
    returncode, stderr = run_encoder(cmd, src, cfg, progress)
    progress.finish(src, info.duration)

    if returncode != 0:
        tmp.unlink(missing_ok=True)
        tail = stderr.strip().splitlines()
        return Result(src, dst, False, tail[-1] if tail else f"ffmpeg failed ({returncode})",
                      info.size, 0)

    problem = verify_output(tmp, info.duration)
    if problem:
        tmp.unlink(missing_ok=True)
        return Result(src, dst, False, problem, info.size, 0)

    if cfg.replace:
        stopped = prepare_replace(info, tmp, dst)
        if stopped is not None:
            return stopped

    tmp.replace(dst)
    return Result(src, dst, True, job.plan.note, info.size, dst.stat().st_size)


# ---------------------------------------------------------------------------
# 入力の収集と出力先の決定
# ---------------------------------------------------------------------------


def collect_inputs(cfg: Config) -> list[Path]:
    """入力を集める。書きかけの一時ファイルと、入力ツリーの内側の出力先は除く。

    `ffmpeg-convert.py . -o compressed` のように出力先を入力の内側に置くのは
    自然な使い方だが、素朴に走査すると2回目の実行で出力済みファイルを入力として
    拾い、再圧縮してしまう。中断時に残る *.part.mp4 は出力先の外（--replace なら
    元ファイルの隣）にも生まれるので、拡張子で別に弾く。
    """
    def under_outdir(p: Path) -> bool:
        return cfg.outdir is not None and (p == cfg.outdir or cfg.outdir in p.parents)

    found: list[Path] = []
    for root in cfg.roots:
        if root.is_file():
            found.append(root)
        elif root.is_dir():
            it = root.rglob("*") if cfg.recursive else root.glob("*")
            found += [p for p in it
                      if p.is_file() and p.suffix.lower() in VIDEO_SUFFIXES
                      and not under_outdir(p) and ".part" not in p.suffixes]
    return sorted(set(found))


def parameter_suffix(info: MediaInfo, cfg: Config) -> str:
    """出力名に添える設定の要約。元ファイルと並べても、設定を変えて作り直しても区別できる。"""
    parts = []
    # 元より小さい指定でなければ縮小は起きないので、そのときは名前にも出さない。
    # 判定は scale_filter に任せて「名前と中身が食い違う」ことを防ぐ。
    if scale_filter(info, cfg.size):
        parts.append(f"{cfg.size}p")
    parts.append(ENCODER_NAMES[cfg.encoder])
    if cfg.crf_explicit:
        parts.append(f"crf{cfg.crf}")     # -q より強いので、こちらだけを出す
    elif cfg.quality != DEFAULT_QUALITY:
        parts.append(cfg.quality)
    if cfg.tune:
        parts.append(cfg.tune)
    if cfg.lecture:
        parts.append("lecture")
    return " ".join(parts)


def destination_for(info: MediaInfo, suffix: str, cfg: Config) -> Path:
    """出力パスを決める。

    単発ファイルの変換では「元名 [720p hevc high].mp4」のように設定を名前に書く。
    元ファイルの隣に置いても区別でき、設定を変えて作り直しても衝突しないため。
    ディレクトリを渡された場合は元の名前のまま、入力の構成を出力先に写す。
    --replace では元の名前をそのまま引き継ぐ（設定を名前に書いても、置き換えた先には
    見比べる相手が残らない）。
    """
    src = info.path
    if cfg.replace:
        # 入れ物が変わらないなら拡張子はそのまま。hello.MP4 を hello.mp4 に
        # 改名するのは求められていない
        return src if src.suffix.lower() == suffix else src.with_suffix(suffix)
    if cfg.output_file is not None:
        return cfg.output_file
    if cfg.single_file:
        parent = cfg.outdir if cfg.outdir is not None else src.parent
        return parent / f"{src.stem} [{parameter_suffix(info, cfg)}]{suffix}"
    for root in cfg.roots:
        if root.is_dir():
            try:
                return (cfg.outdir / src.relative_to(root)).with_suffix(suffix)
            except ValueError:
                continue
    return (cfg.outdir / src.name).with_suffix(suffix)


# ---------------------------------------------------------------------------
# コマンドライン
# ---------------------------------------------------------------------------


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

    --replace は出力先が元ファイルの場所に決まるので、-o を受け取る余地がない。
    """
    args.single_file = len(args.inputs) == 1 and args.inputs[0].is_file()
    args.output_file = None

    if args.replace:
        if args.output is not None:
            parser.error("--replace は -o/--output と併用できません（出力先は元ファイルの場所です）")
        args.outdir = None
        return

    if args.output is None:
        # 単発ファイルは元と同じ場所へ。ディレクトリ入力は compressed/ へ。
        args.outdir = None if args.single_file else Path("compressed").resolve()
        return

    container = CONTAINER_SUFFIXES.get(args.output.suffix.lower())
    if container is None or args.output.is_dir():
        args.outdir = args.output.resolve()
        return

    if not args.single_file:
        parser.error(f"-o にファイル名を指定できるのは単発ファイルの変換時だけです"
                     f"（{args.output} をディレクトリにするか、入力を1ファイルにしてください）")
    # 拡張子が出力コンテナも決める。--container で別のものを明示されていたら矛盾。
    if args.container not in ("auto", container):
        parser.error(f"-o {args.output.name} は --container {args.container} と矛盾します")
    args.container = container
    args.output_file = args.output.resolve()
    args.outdir = args.output_file.parent


def validate_combinations(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """成り立たない指定の組み合わせを、解析を始める前に弾く。

    黙って片方を上書きすると「指定したのに効かない」になるので、必ずエラーで返す。
    ここで見るのは両方が明示された場合だけ。片方がautoで結果的に食い違う場合は、
    本数ごとに container_audio_conflict が見る。
    """
    if args.tune and args.encoder is not None and args.encoder not in TUNE_ENCODERS:
        parser.error(f"-t/--tune は {ENCODER_NAMES[args.encoder]} では効きません"
                     "（x264/x265のみ。ffmpegのlibsvtav1は-tuneを黙って無視します）")

    if args.apple:
        # --apple が担うのは「入れ物と音声」だけで、映像コーデックには手を出さない。
        # MP4+AACは機種に関係なくAVFoundationが扱える一方、どの映像コーデックが
        # 再生できるかは機種依存（AV1はA17 Pro / M3以降のみ）なので、そこは
        # --hevc / --av1 の判断に委ねる。だから --apple --av1 は矛盾ではない。
        if args.audio_codec == "opus":
            parser.error("--apple は --audio-codec opus と併用できません（AVFoundationにOpusデコーダがありません）")
        if args.container not in ("auto", "mp4"):
            parser.error(f"--apple は --container {args.container} と併用できません")

    if args.container == "mp4" and args.audio_codec == "opus":
        parser.error("--container mp4 は --audio-codec opus と併用できません"
                     "（AVFoundationにOpusデコーダがありません）")
    if args.container == "webm":
        if args.audio_codec == "aac":
            parser.error("--container webm は --audio-codec aac と併用できません（WebMはOpus/Vorbisのみ）")
        if args.encoder is not None and args.encoder not in WEBM_VIDEO_CODECS:
            parser.error(f"--container webm は {args.encoder} を収容できません（--av1 と併用してください）")
        if args.tune:
            parser.error("--container webm は -t/--tune と併用できません"
                         "（WebMに入るのはAV1/VP9で、-tune が効くのは x264/x265 だけです）")


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
    p.add_argument("-q", "--quality", choices=QUALITY_CHOICES, default=argparse.SUPPRESS,
                   help=f"品質段階。コーデックと素材ごとのCRF表を引く"
                        f"（既定は {DEFAULT_QUALITY}。端末実行なら聞く）")
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
    p.add_argument("--overwrite", action="store_true",
                   help="出力が既にあっても上書きする（既定はスキップ）")
    p.add_argument("--replace", action="store_true",
                   help="変換結果で元ファイルを置き換える（元はゴミ箱へ / -o とは併用不可）")
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
    args.quality = getattr(args, "quality", None)
    # --crf を明示されたかは出力ファイル名にも出すので覚えておく
    args.crf_explicit = args.crf is not None
    # 以降はすべて絶対パスで扱う（出力先が入力ツリーの内側かの判定が単純になる）
    args.inputs = [p.resolve() for p in args.inputs]

    # ffmpegの有無は対話で質問する前に確かめる。--help はここに到達しないので、
    # ffmpegが無い環境でも使い方だけは読める。
    missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing:
        p.exit(1, f"{' / '.join(missing)} が見つかりません\n")

    if args.replace and sys.platform != "darwin":
        p.error("--replace はmacOS専用です（元ファイルの退避先が ~/.Trash 決め打ちのため）")

    resolve_output_target(p, args)
    validate_combinations(p, args)
    return args


# ---------------------------------------------------------------------------
# 対話による設定の確定
# ---------------------------------------------------------------------------


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


def resolve_options(args: argparse.Namespace) -> Config:
    """未指定のオプションを対話か既定値で埋め、実行設定を組み立てる。

    端末から人が実行したときだけ質問する。パイプ・cron・--no-interactive では
    黙って既定（HEVC + MP4）に落ちるので、バッチ実行の挙動は変わらない。
    """
    interactive = args.interactive and sys.stdin.isatty() and sys.stdout.isatty()
    answered: list[str] = []

    content = args.content
    if content is None:
        if interactive:
            content = prompt_choice("素材の種類を選んでください", CONTENT_CHOICES, DEFAULT_CONTENT)
            if content != DEFAULT_CONTENT:
                answered.append(f"--{content}")
        else:
            content = DEFAULT_CONTENT
    lecture = content == "lecture"

    size = args.size
    if size is None:
        if interactive:
            chosen = prompt_choice("出力解像度を選んでください", SIZE_CHOICES, SIZE_SOURCE)
            size = parse_size(chosen)
            if chosen != SIZE_SOURCE:
                answered.append(f"-s {chosen}")
        else:
            size = 0

    apple, container, audio_codec = args.apple, args.container, args.audio_codec

    # Apple互換を先に聞く。ここでYesなら入れ物と音声が決まり、後の音声の質問が要らなくなる。
    # --apple が固定するのは入れ物と音声だけ。矛盾する指定があるときは聞かない。
    if interactive and not apple and audio_codec != "opus" and container in ("auto", "mp4"):
        apple = prompt_choice(
            "Apple機（写真.app / ファイル.app / QuickTime）で開ける形に固定しますか",
            [("no", "しない — 入れ物と音声は入力に合わせて決める"),
             ("yes", "する — MP4 + AAC に固定する")],
            "no",
        ) == "yes"
        if apple:
            answered.append("--apple")

    encoder = args.encoder
    if encoder is None:
        # 明示された --container / -t に合わないコーデックは選ばせない
        choices = [(value, label) for value, label in ENCODER_CHOICES
                   if (container != "webm" or value in WEBM_VIDEO_CODECS)
                   and (not args.tune or value in TUNE_ENCODERS)]
        fallback = DEFAULT_ENCODER if any(v == DEFAULT_ENCODER for v, _ in choices) else choices[0][0]
        if len(choices) == 1:
            encoder = choices[0][0]
        elif interactive:
            encoder = prompt_choice("映像コーデックを選んでください", choices, fallback)
            answered.append(f"--{ENCODER_NAMES[encoder]}")
        else:
            encoder = fallback

    quality = args.quality
    if quality is None:
        # --crf を明示されていれば -q は使われない。聞いても答えが捨てられるだけ
        if interactive and args.crf is None:
            crf_map = crf_table(lecture, encoder)
            quality = prompt_choice(
                "画質を選んでください",
                [(value, f"{label}（CRF {crf_map[value]}）") for value, label in QUALITY_DESCRIPTIONS],
                DEFAULT_QUALITY,
            )
            if quality != DEFAULT_QUALITY:
                answered.append(f"-q {quality}")
        else:
            quality = DEFAULT_QUALITY

    if apple:
        audio_codec, container = "aac", "mp4"
    elif container == "mp4" and audio_codec == "auto" and encoder == "libsvtav1":
        # MP4を指定されている。autoのままではOpusになるが、MP4のOpusはQuickTimeで
        # 鳴らないので、明示されたコンテナを優先してAACへ寄せる。
        audio_codec = "aac"

    # 入れ物を明示されていると、そこに入る音声も決まるので選ぶ余地がない
    # （MP4のOpusはQuickTimeで鳴らず、WebMにAACは入らない）。--apple も上の行で
    # aac を入れているので、ここは素通りする。
    if interactive and audio_codec == "auto" and container in ("auto", "mkv"):
        audio_codec = prompt_choice("音声コーデックを選んでください",
                                    AUDIO_CODEC_CHOICES, DEFAULT_AUDIO_CODEC)
        if audio_codec != DEFAULT_AUDIO_CODEC:
            answered.append(f"--audio-codec {audio_codec}")

    if answered:
        print(f"（次回から {' '.join(answered)} を付けるか、--no-interactive で質問を省けます）")

    return Config(
        roots=tuple(args.inputs),
        outdir=args.outdir,
        output_file=args.output_file,
        single_file=args.single_file,
        recursive=args.recursive,
        overwrite=args.overwrite,
        replace=args.replace,
        encoder=encoder,
        size=size,
        quality=quality,
        crf=args.crf if args.crf is not None else crf_table(lecture, encoder)[quality],
        crf_explicit=args.crf_explicit,
        preset=args.preset if args.preset is not None else DEFAULT_PRESET[encoder],
        tune=args.tune,
        # 汎用素材ではエンコーダの既定に任せる（0で「指定しない」を表す）
        gop_seconds=args.gop_seconds if args.gop_seconds is not None
        else (LECTURE_GOP_SECONDS if lecture else 0.0),
        lecture=lecture,
        apple=apple,
        container=container,
        audio_mode=args.audio_mode,
        audio_codec=audio_codec,
        audio_bitrate=args.audio_bitrate,
        mono_bitrate=args.mono_bitrate,
        jobs=args.jobs,
        dry_run=args.dry_run,
        verbose=args.verbose,
        progress=args.progress,
    )


# ---------------------------------------------------------------------------
# 全体の進行
# ---------------------------------------------------------------------------


def announce(cfg: Config, total: int) -> None:
    """これから何をどこへ書くのかを最初に伝える。"""
    if cfg.apple and cfg.encoder == "libsvtav1":
        # 通すが、再生できる機種が限られることは黙っていられない。
        print("注意: AV1はA17 Pro / M3世代以降のApple機でのみ再生できます"
              "（M1・M2世代では再生できません）")
    if cfg.replace:
        print("出力先: 元ファイルと同じ場所（元ファイルはゴミ箱へ移します）")
    else:
        print(f"出力先: {cfg.output_file or cfg.outdir or cfg.roots[0].parent}"
              "（元ファイルは変更しません）")
    print(f"{total} 本を解析中…")


def plan_jobs(sources: list[Path], cfg: Config) -> tuple[list[Job], int]:
    """1本ずつ解析して変換内容を決める。

    (変換する仕事の一覧, 解析・組み合わせの都合で処理できなかった本数) を返す。
    後者は終了コードに出す。既に出力がある等で意図どおり飛ばした分は数えない。
    """
    jobs: list[Job] = []
    skipped = 0
    for src in sources:
        try:
            info = probe(src)
        except (ProbeError, json.JSONDecodeError) as exc:
            print(f"  NG     {src.name}: {exc}", file=sys.stderr)
            skipped += 1
            continue

        # コンテナは音声の計画で決まる（Opusを使うならMKV）ので、先に立てる
        plan = build_audio_args(info, cfg)
        suffix = container_suffix(plan, cfg)
        conflict = container_audio_conflict(plan, info, suffix, cfg)
        if conflict:
            print(f"  NG     {src.name}: {conflict}", file=sys.stderr)
            skipped += 1
            continue
        dst = destination_for(info, suffix, cfg)
        # --replace で拡張子が変わらないときは dst が src そのもの。それは想定どおり
        # 大文字小文字を区別しないAPFSでは hello.MP4 と hello.mp4 は同じファイル。
        # 文字列で比べると別物に見えるので、inode で確かめる
        same_path = dst.exists() and dst.samefile(src)
        if same_path and not cfg.replace:
            print(f"  skip   {src.name}（出力先が入力と同一）")
            continue
        if dst.exists() and not same_path and not cfg.overwrite:
            print(f"  skip   {src.name}（出力が既にあります。作り直すなら --overwrite）")
            continue

        audio_desc = "音声なし"
        if info.audio:
            kbps = f"{info.audio.bitrate // 1000}k" if info.audio.bitrate else "?"
            audio_desc = f"{info.audio.codec} {info.audio.channels}ch {kbps}"
        print(f"  {src.name}: {info.width}x{info.height} {info.fps:.3g}fps "
              f"{info.video_codec} / {audio_desc} / {human(info.size)}")
        jobs.append(Job(info, dst, plan))
    return jobs, skipped


def settings_summary(cfg: Config) -> str:
    """「hevc / CRF 28 / preset medium / …」という設定の一行要約。"""
    settings = [ENCODER_NAMES[cfg.encoder], f"CRF {cfg.crf}", f"preset {cfg.preset}"]
    if cfg.size:
        settings.append(f"短辺{cfg.size}px以下へ縮小")
    if cfg.tune:
        settings.append(f"tune {cfg.tune}")
    if cfg.lecture:
        settings.append("講演スライド向け")
    return " / ".join(settings)


def run_jobs(jobs: list[Job], cfg: Config, layout: ResultLayout) -> list[Result]:
    """まとめてエンコードし、終わった順に結果行を出す。"""
    print(f"\n{len(jobs)} 本を {settings_summary(cfg)} で圧縮します（並列 {cfg.jobs}）")
    results: list[Result] = []
    with (ProgressReporter.for_jobs(jobs, cfg, layout) as progress,
          ThreadPoolExecutor(max_workers=max(cfg.jobs, 1)) as pool):
        futures = [pool.submit(encode, job, cfg, progress) for job in jobs]
        for done, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            results.append(result)
            prefix = layout.prefix(done, result.src.name)
            if not result.ok:
                progress.report(f"{prefix} NG {result.message}", error=True)
            elif result.kept:
                progress.report(f"{prefix} {result.message}")
            elif not cfg.dry_run:
                progress.report(f"{prefix} {size_change(result.src_size, result.dst_size)}"
                                f" / {result.message}")
    return results


def report(results: list[Result], skipped: int, layout: ResultLayout) -> int:
    """結果をまとめて、終了コードを返す。"""
    ok = [r for r in results if r.ok]
    kept = [r for r in ok if r.kept]
    src_total = sum(r.src_size for r in ok)
    dst_total = sum(r.dst_size for r in ok)
    print(f"\n完了 {len(ok)}/{len(results)} 本")
    if kept:
        print(f"うち {len(kept)} 本は元より大きくなったため置き換えていません")
    if src_total:
        # 結果行と同じ欄に合計を置く
        print(f"{layout.label('合計')} {size_change(src_total, dst_total, show_saved=True)}")
    return 0 if len(ok) == len(results) and not skipped else 1


def main(argv: list[str]) -> int:
    cfg = resolve_options(parse_args(argv))
    sources = collect_inputs(cfg)
    if not sources:
        print("対象の動画が見つかりませんでした", file=sys.stderr)
        return 1

    announce(cfg, len(sources))
    jobs, skipped = plan_jobs(sources, cfg)
    if not jobs:
        print("処理対象がありません")
        return 1 if skipped else 0

    layout = ResultLayout.for_jobs(jobs)
    results = run_jobs(jobs, cfg, layout)
    if cfg.dry_run:
        return 1 if skipped else 0
    return report(results, skipped, layout)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
