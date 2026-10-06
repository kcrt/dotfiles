#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
"""動画をH.264/HEVC/AV1へ再圧縮する。単発でもディレクトリ丸ごとでも使える。

入力は先にまとめてffprobeで解析し、解像度・フレームレート・音声コーデック・チャンネル
構成に応じて設定を組み立てる。音声はコピーで済むなら再エンコードせず、デュアルモノ
（ステレオだが左右が同一）なら1chにまとめる。出力コンテナは映像・音声の
組み合わせから決めるので、再生できない組み合わせが出来上がることはない。

音声が複数あるファイルでは、既定で先頭のトラックだけを残す。--audio-tracks all で
全部、--audio-lang jpn で言語を指定して残せる（指定した言語が無いファイルは先頭）。
字幕は既定で持ち越す。MKVはそのまま、MP4/WebMはテキスト字幕を変換して入れ、
ビットマップ字幕（PGS・VobSub）は入れる手段が無いので落とす。

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
場合は、どれにするかを対話で聞く。加えて、解析の結果そう聞く理由があるときだけ、
複数音声のどれを残すかと、入れ物に入らない字幕を落としてよいかを聞く。
パイプ・cron・--no-interactive では何も聞かず既定（汎用素材 + 元の解像度 + HEVC +
normal + MP4 + 先頭の音声 + 入る字幕）で走る。

-o でディレクトリを指定して対話したときは、最後に設定を保存するか聞く。保存すると
出力先に .ffmpeg-convert（JSON）ができ、次回同じ -o を指定したときは質問せずに
その設定を使う（端末以外から実行しても使う）。コマンドラインで明示したオプションは
保存した設定より優先する。読まずに聞き直すときは --no-saved-settings。
.ffmpeg-convert があるディレクトリは別の変換の出力先とみなし、入力の走査から外す
（外すたびに「スキップ: …」と出す）。同じ入力から出力先を変えて作り分けても、
前の出力を入力として拾わない。
  ffmpeg-convert.py . -o out                     初回は質問し、最後に保存するか聞く
  ffmpeg-convert.py new/ -o out                  2回目以降は out/.ffmpeg-convert を使う

変換中も他の作業が重くならないよう、既定で nice 19（最低優先度）で走る。
ffmpeg/ffprobe はこの優先度を引き継ぐ。空いているマシンでは実質遅くならない。
優先度を下げたくないときは --nice 0。
"""

from __future__ import annotations

import argparse
import functools
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

# 同じディレクトリの script/lib/。uv run は sys.path[0] をこのスクリプトの実体の
# あるディレクトリにするので（シンボリックリンク経由でも解決される）、
# パスをいじらずにそのまま import できる。
# lib 側は標準ライブラリだけで書くこと。PEP 723 の dependencies はこのスクリプトに
# しか書けないため。
from lib.humanize import clock, common_unit, human, size_change
from lib.progressbar import BarSlot, LiveLine, rainbow_rgb, wave_level
from lib.prompt import confirm, interactive as stdio_is_interactive, prompt_choice
from lib.termcolor import RGB, hue_rgb, paint, scale_rgb, status_line
from lib.termtext import display_width, pad_display, truncate_display
from lib.trash import move_to_trash

VIDEO_SUFFIXES = frozenset({".mp4", ".mov", ".m4v", ".mkv", ".avi", ".wmv", ".flv", ".ts", ".webm"})

# 左右チャンネル差がこの値(dBFS)を下回れば実質デュアルモノとみなす
DUAL_MONO_MAX_DB = -60.0
# 非可逆音声がこのビットレート以下なら、再エンコードは世代劣化を足すだけなのでコピーする
LOSSY_COPY_MAX_BITRATE = 256_000
# 音声解析に使うサンプル長（秒）
AUDIO_PROBE_SECONDS = 180

# 入力の解析（ffprobe）を並列で走らせる本数。-j とは別物で、あちらはエンコーダ用。
# ffmpegは1本でコアを使い切るので -j の既定は1だが、ffprobeは待ち時間が主なので
# 並べたほうが速い。解析は対話より前にあり、ここで待たせると質問に辿り着けない。
PROBE_WORKERS = min(8, os.cpu_count() or 4)

# 解析行を1本ずつ出すのはこの本数まで。超えたら集計だけにする。
# でないと大量の行でウィザードの質問が画面外へ流れてしまう。
SCAN_DETAIL_MAX = 20

# 既定の nice 値。エンコードは長時間コアを使い切るので、最低優先度で走らせて
# 対話的な作業を邪魔しないようにする。
DEFAULT_NICE = 19

# MP4に入れても広く再生できる音声コーデック。Opus/Vorbisは規格上MP4に入るが
# QuickTime/Safariが再生できないため、コピーせずAACに変換する。
MP4_PLAYABLE_AUDIO_CODECS = frozenset({"aac", "mp3", "ac3", "eac3", "alac"})

# --apple 指定時に「そのままコピーしてよい」と認める音声コーデック。
# MP3やAC3もMP4コンテナには入るが、AVFoundationでの扱いが環境によって怪しいので
# QuickTime/写真/iOSで確実に鳴る2つだけに絞る。
APPLE_PLAYABLE_AUDIO_CODECS = frozenset({"aac", "alac"})

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
# 進捗行でファイル名に譲る表示幅の上限。長い名前にバーを潰させない。
BAR_NAME_MAX_WIDTH = 24

# 速度帯 → バーの色（下限, RGB）。実時間に対する倍率で、1.0が等速。
# 「赤＝待たされる / 緑＝等速より速い / 青＝快調」が一目で分かるようにする。
# バーの描き方そのものは lib.progressbar が持っている。ここにあるのは
# 「倍速という尺度をどう色に割り当てるか」という、動画再圧縮に固有の部分だけ。
SPEED_COLORS = [
    (0.0, (215, 60, 50)),     # 赤 —— 等速の1/3未満。かなり遅い
    (0.3, (220, 130, 30)),    # オレンジ
    (1.0, (70, 190, 90)),     # 緑 —— 実時間より速い
    (3.0, (70, 145, 240)),    # 青
]

# これ以上はレインボー。色相がバー内を流れる。
RAINBOW_SPEED = 7.0

# 失敗した本の印。大量の行が流れる中から拾えることが目的なので、赤はNGだけに使う。
# skip は意図どおり飛ばした印なので色を付けない（付けると赤が埋もれる）。
NG_RGB = (215, 60, 50)    # 速度帯の赤と同じ
# 変換はするが黙って欠けるものがある、の印。再圧縮して太った本と同系統のオレンジ。
NOTE_RGB = (220, 130, 30)

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

# コマンドラインの選択肢。保存した設定ファイルの検証でも同じものを使う。
AUDIO_MODE_OPTIONS = ("auto", "prefer-copy", "mono", "stereo")
AUDIO_CODEC_OPTIONS = ("auto", "aac", "opus")
CONTAINER_OPTIONS = ("auto", "mp4", "mkv", "webm")
AUDIO_TRACK_OPTIONS = ("first", "all", "lang")
SUBTITLE_OPTIONS = ("keep", "drop")

# -o の出力先ディレクトリに置く設定ファイル。対話で決めた設定を保存しておき、
# 次回同じ -o を指定したときは質問せずにこれを使う。
SETTINGS_FILENAME = ".ffmpeg-convert"
SETTINGS_VERSION = 1


def _is_positive_int(value: object) -> bool:
    return type(value) is int and value > 0


# 設定ファイルに書くキー（argparse の dest と同じ名前）→ 値の検証。
# 手で編集されることもあるので、読むときは型まで確かめる。
SETTINGS_VALIDATORS: dict[str, Callable[[object], bool]] = {
    "content": lambda v: v in ("general", "lecture"),
    "size": lambda v: type(v) is int and v >= 0,
    "apple": lambda v: type(v) is bool,
    "encoder": lambda v: v in ENCODER_NAMES,
    "quality": lambda v: v in QUALITY_CHOICES,
    "crf": lambda v: type(v) is int,
    "tune": lambda v: isinstance(v, str) and bool(v),
    "preset": lambda v: isinstance(v, str) and bool(v),
    "gop_seconds": lambda v: type(v) in (int, float) and v >= 0,
    "audio_mode": lambda v: v in AUDIO_MODE_OPTIONS,
    "audio_codec": lambda v: v in AUDIO_CODEC_OPTIONS,
    "container": lambda v: v in CONTAINER_OPTIONS,
    "audio_bitrate": _is_positive_int,
    "mono_bitrate": _is_positive_int,
    "audio_tracks": lambda v: v in AUDIO_TRACK_OPTIONS,
    "audio_lang": lambda v: (isinstance(v, list) and bool(v)
                             and all(isinstance(code, str) and code for code in v)),
    "subtitles": lambda v: v in SUBTITLE_OPTIONS,
}

# コマンドラインで指定されなかったときの値。これと違えば「明示された」とみなし、
# 保存した設定より優先する。ここに無いキーは None が未指定。
SETTINGS_UNSET_VALUES: dict[str, object] = {
    "apple": False, "audio_mode": "auto", "audio_codec": "auto",
    "container": "auto", "subtitles": "keep",
}

# 一緒でないと意味をなさない設定の組。どれか1つでもコマンドラインで指定されたら、
# 組の残りも保存した値を使わない。たとえば --hevc を付けたのに、保存したAV1用の
# CRFやpresetが残ると目盛りが合わない。--container mkv を付けたのに保存した
# --apple が残ると矛盾する。
SETTINGS_LINKED_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"encoder", "tune", "crf", "preset"}),
    frozenset({"quality", "crf"}),
    frozenset({"apple", "container", "audio_codec"}),
    frozenset({"audio_tracks", "audio_lang"}),
)

# テキスト字幕。MP4のmov_text・WebMのwebvttへ変換できる。
# ここに無いものは全て非テキスト扱いにする（変換先が無いので落とすしかない）。
TEXT_SUBTITLE_CODECS = frozenset({
    "subrip", "srt", "ass", "ssa", "mov_text", "webvtt", "text", "eia_608",
    "subviewer", "subviewer1", "microdvd", "mpl2", "jacosub", "sami", "stl", "realtext",
})

# 入れ物ごとの字幕コーデック。MKVは何でも入るのでcopy、MP4/WebMは変換して入れる。
# ビットマップ字幕（PGS・VobSub）はMP4/WebMに入れる手段が無いので落とすしかない。
SUBTITLE_CONTAINER_CODEC = {".mkv": "copy", ".mp4": "mov_text", ".webm": "webvtt"}

# 言語タグとして意味を持たない値。指定しても選びようがないので選択肢に出さない。
UNKNOWN_LANGUAGES = frozenset({"und", "unk", "none", "mis", "zxx"})

# 対話で言語を提示するときの表示名。ここに無いコードはそのまま出す。
LANGUAGE_NAMES = {
    "jpn": "日本語", "eng": "英語", "chi": "中国語", "zho": "中国語", "kor": "韓国語",
    "fra": "フランス語", "fre": "フランス語", "deu": "ドイツ語", "ger": "ドイツ語",
    "spa": "スペイン語", "ita": "イタリア語", "por": "ポルトガル語", "rus": "ロシア語",
}


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
    crf: int
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
    audio_tracks: str                # "first" / "lang" / "all"
    audio_langs: tuple[str, ...]     # audio_tracks が "lang" のときだけ中身がある
    subtitles: str                   # "keep" / "drop"

    # --- 実行のしかた ---
    jobs: int
    dry_run: bool
    verbose: bool
    progress: bool

    @property
    def mp4_audio_codecs(self) -> frozenset[str]:
        """MP4に入れてそのまま鳴ると認める音声コーデック。--apple ならより厳しく絞る。"""
        return APPLE_PLAYABLE_AUDIO_CODECS if self.apple else MP4_PLAYABLE_AUDIO_CODECS

@dataclass(frozen=True)
class AudioInfo:
    codec: str | None
    channels: int
    sample_rate: int
    bitrate: int | None
    # 音声ストリーム内での通し番号。ffmpegの 0:a:{index} と揃える。
    # 全ストリーム中の index ではないことに注意（そちらは映像や字幕を含む）
    index: int = 0
    language: str | None = None   # 小文字3文字。und・未設定は None
    title: str | None = None
    default: bool = False

    @property
    def lossy(self) -> bool:
        """非可逆コーデックか。可逆・非圧縮ならモノ化・再エンコードの効果が大きい。"""
        return (self.codec or "").lower() in LOSSY_AUDIO_CODECS

    @property
    def label(self) -> str:
        """複数トラックを並べて見せるときの短い見出し。"""
        return self.title or LANGUAGE_NAMES.get(self.language or "", self.language or "言語不明")


@dataclass(frozen=True)
class SubtitleInfo:
    codec: str | None
    index: int = 0
    language: str | None = None
    default: bool = False
    forced: bool = False

    @property
    def text_based(self) -> bool:
        """テキスト字幕か。ビットマップ字幕はMP4/WebMへ変換する手段が無い。

        知らないコーデックは非テキスト扱いにする。mov_text/webvttへ変換できると
        誤認すると、ffmpegがそのファイルごと失敗する。
        """
        return (self.codec or "").lower() in TEXT_SUBTITLE_CODECS


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
    audios: tuple[AudioInfo, ...] = ()
    subtitles: tuple[SubtitleInfo, ...] = ()


@dataclass(frozen=True)
class TrackPlan:
    """音声1トラックの扱い方。入力のどれを、何にするか。"""

    source: AudioInfo
    codec: str = "copy"          # "copy" / "aac" / "libopus"
    channels: int | None = None  # copyのときはNone（元のまま）
    bitrate: int | None = None   # kbps。copyのときはNone
    note: str = ""

    @property
    def out_codec_name(self) -> str | None:
        """出力に入るストリームのcodec_name。コンテナ適合の判定に使う。"""
        if self.codec == "copy":
            return (self.source.codec or "").lower() or None
        return ENCODER_CODEC_NAME.get(self.codec, self.codec)


@dataclass(frozen=True)
class AudioPlan:
    args: list[str]                     # -map と -c:a を含む音声まわり全体
    note: str
    tracks: tuple[TrackPlan, ...] = ()

    @property
    def needs_matroska(self) -> bool:
        """OpusをMP4に入れるとmacOSがデコードできない（実測でafconvertが失敗）ため避ける。

        規格上はISOBMFFへのOpusカプセル化が定義されているが、AVFoundationに
        Opusデコーダが無いのでQuickTimeでは音が出ない。
        """
        return any(t.codec == "libopus" for t in self.tracks)


@dataclass(frozen=True)
class SubtitlePlan:
    args: list[str]
    dropped: tuple[SubtitleInfo, ...] = ()   # 入れ物に入らず落とすもの。plan_jobsが報告する
    note: str = ""


@dataclass(frozen=True)
class Job:
    """1本分の変換内容。解析の時点で確定し、そのままエンコードへ渡る。"""

    info: MediaInfo
    dst: Path
    plan: AudioPlan
    subs: SubtitlePlan


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
def measure_channel_difference(path: Path, track: int = 0) -> float:
    """L-R の最大音量を dBFS で返す。無音（＝左右同一）なら大きな負の値。

    音声を実際にデコードするので安くはない。再エンコードすると決まった後に
    「ついでにモノへまとめられるか」を判断するためだけに呼ぶこと。
    コピーで済む入力に対しては呼ばれない。

    track は音声ストリーム内の通し番号。省くとキャッシュが path だけで引かれ、
    2本目の判定に1本目の測定値を返してしまう。

    -vn は必須。filter_complex が 1本しか使っていなくても、-map が無いと
    ffmpegの自動ストリーム選択が映像も拾い、null muxerへ向けて律儀に全フレームを
    デコードしてしまう（1080p・180秒で実測5秒）。音量の測定値は -vn の有無で変わらない。
    """
    filt = (
        f"[0:a:{track}]channelsplit=channel_layout=stereo[l][r];"
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
    return (audio.channels == 2
            and measure_channel_difference(path, audio.index) < DUAL_MONO_MAX_DB)


def estimate_audio_bitrate(path: Path, index: int = 0, seconds: int = 60) -> int | None:
    """ストリームのbit_rateが未記載のとき（mkv等でよくある）、実パケットから推定する。"""
    # csv出力は要求した順ではなくffprobe内部のフィールド順で並ぶため、jsonで受ける
    try:
        data = run_json([
            "ffprobe", "-v", "error", "-print_format", "json",
            "-select_streams", f"a:{index}",
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


def stream_tag(stream: dict, name: str) -> str | None:
    """ストリームのタグを大文字小文字を無視して引く。

    MP4/MOVが 'Language'、Matroskaが 'language' と書くなど揺れがあるので、
    綴りをそのまま突き合わせると取りこぼす。
    """
    for key, value in (stream.get("tags") or {}).items():
        if key.lower() == name and isinstance(value, str) and value.strip():
            return value.strip()
    return None


def normalize_language(value: str | None) -> str | None:
    """言語タグを小文字に揃える。「未設定」を意味する値は None に潰す。

    und を残すと対話の選択肢に「und」が並んでしまうが、それを選んでも
    何も指定していないのと同じで意味がない。
    """
    code = (value or "").strip().lower()
    return None if not code or code in UNKNOWN_LANGUAGES else code


def has_disposition(stream: dict, name: str) -> bool:
    return bool((stream.get("disposition") or {}).get(name))


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

    audios = tuple(
        AudioInfo(
            codec=stream.get("codec_name"),
            channels=to_int(stream.get("channels")) or 1,
            sample_rate=to_int(stream.get("sample_rate")) or 48_000,
            # bit_rate が無いときだけ実測する。トラック数ぶん走るので空振りは避ける
            bitrate=to_int(stream.get("bit_rate")) or estimate_audio_bitrate(path, index),
            index=index,
            language=normalize_language(stream_tag(stream, "language")),
            title=stream_tag(stream, "title"),
            default=has_disposition(stream, "default"),
        )
        for index, stream in enumerate(s for s in streams if s.get("codec_type") == "audio")
    )

    subtitles = tuple(
        SubtitleInfo(
            codec=stream.get("codec_name"),
            index=index,
            language=normalize_language(stream_tag(stream, "language")),
            default=has_disposition(stream, "default"),
            forced=has_disposition(stream, "forced"),
        )
        for index, stream in enumerate(s for s in streams if s.get("codec_type") == "subtitle")
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
        audios=audios,
        subtitles=subtitles,
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
    if (cfg.encoder in WEBM_VIDEO_CODECS
            and all(t.codec in WEBM_AUDIO_CODECS for t in plan.tracks)):
        return ".webm"
    return ".mkv"


def output_audio_codecs(plan: AudioPlan) -> list[str]:
    """出力に入る音声のcodec_nameを並び順に。音声を落とす場合は空。"""
    return [name for name in (t.out_codec_name for t in plan.tracks) if name]


def container_audio_conflict(plan: AudioPlan, suffix: str, cfg: Config) -> str | None:
    """コンテナに入らない音声の組み合わせを、ffmpegを起動する前に見つける。

    --container を明示するとauto時の安全な組み合わせから外れることがある。
    そのままffmpegに渡すと "Nothing was written into output file" のような
    原因の分からないエラーで落ちるので、理由を添えて先に弾く。
    収容制限を持たないコンテナ（.mkv）は常に通す。

    スキップはファイル単位なので、1本でも入らないトラックがあればその時点で弾く。
    """
    allowed = {".mp4": cfg.mp4_audio_codecs, ".webm": WEBM_AUDIO_CODEC_NAMES}.get(suffix)
    if allowed is None:
        return None
    for codec in output_audio_codecs(plan):
        if codec not in allowed:
            return (f"{suffix.lstrip('.')} に {codec} 音声は入れられません"
                    f"（--container / --audio-codec / --audio-mode を見直してください）")
    return None


def container_audio_warning(plan: AudioPlan, suffix: str) -> str | None:
    """入るには入るが、そう再生されるとは限らない組み合わせ。弾かずに一言添える。"""
    if suffix == ".webm" and len(plan.tracks) > 1:
        return (f"{len(plan.tracks)}本の音声をwebmに入れますが、"
                "1本目しか再生しない環境がほとんどです（mkvなら選べます）")
    return None


def resolve_audio_codec_for(audio_codec: str, encoder: str) -> str:
    """再エンコードする場合に使う音声コーデック。

    AV1を選んだ場合はアーカイブ用途とみなし、対になるOpusを既定にする。
    映像が半分になると音声が容量の約半分を占めるようになるため。
    """
    if audio_codec == "opus":
        return "libopus"
    if audio_codec == "aac":
        return "aac"
    return "libopus" if encoder == "libsvtav1" else "aac"


def resolve_audio_codec(cfg: Config) -> str:
    return resolve_audio_codec_for(cfg.audio_codec, cfg.encoder)


def predicted_suffix(container: str, audio_codec: str, encoder: str) -> str:
    """設定が固まった時点で分かる出力拡張子。対話で字幕の可否を見積もるのに使う。

    実際の拡張子は container_suffix がトラックごとの計画から決めるが、そちらも
    「Opusを使うか」だけで分岐するので、Configが固まれば全ファイルで同じになる。

    唯一ずれるのが --audio-mode prefer-copy × Opus で、入力の音声をコピーできた
    ファイルだけMP4に落ち着く。その場合ここはMKVと見積もって字幕の質問を省くが、
    落ちる字幕は plan_jobs が「注意」として報告するので黙って消えることはない。
    """
    if container != "auto":
        return f".{container}"
    if resolve_audio_codec_for(audio_codec, encoder) != "libopus":
        return ".mp4"
    return ".webm" if encoder in WEBM_VIDEO_CODECS else ".mkv"


def plan_one_track(audio: AudioInfo, info: MediaInfo, cfg: Config) -> TrackPlan:
    """音声1トラックをコピーするか、何に再エンコードするかを決める。"""
    codec = (audio.codec or "").lower()
    plays_as_is = codec in cfg.mp4_audio_codecs
    kbps = audio.bitrate // 1000 if audio.bitrate else None
    out_codec = resolve_audio_codec(cfg)

    def encode(channels: int, reason: str) -> TrackPlan:
        override = cfg.mono_bitrate if channels == 1 else cfg.audio_bitrate
        target = override if override else DEFAULT_AUDIO_BITRATE[out_codec][channels]
        layout = "mono" if channels == 1 else "stereo"
        name = ENCODER_CODEC_NAME.get(out_codec, out_codec)
        return TrackPlan(audio, out_codec, channels, target,
                         f"{name} {target}k {layout} ({reason})")

    def copy(reason: str) -> TrackPlan:
        return TrackPlan(audio, "copy", note=f"copy ({reason})")

    if cfg.audio_mode == "mono":
        return encode(1, "指定")
    if cfg.audio_mode == "stereo":
        return encode(min(audio.channels, 2), "指定")
    if cfg.audio_mode == "prefer-copy":
        if plays_as_is:
            return copy(f"{codec} {audio.channels}ch")
        return encode(min(audio.channels, 2), f"{codec}から変換")

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
    if audio.lossy and plays_as_is:
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
    if not plays_as_is:
        return encode(downmixed(), f"{codec}から変換")
    return encode(downmixed(), f"{kbps}kから圧縮")


def select_audio_tracks(info: MediaInfo, cfg: Config) -> tuple[AudioInfo, ...]:
    """どの音声トラックを残すか。"""
    if not info.audios:
        return ()
    if cfg.audio_tracks == "all":
        return info.audios
    if cfg.audio_tracks == "lang":
        picked = tuple(a for a in info.audios if a.language in cfg.audio_langs)
        if picked:
            return picked
        # 指定した言語を持たないファイル。音のない動画を作るよりは先頭を残す。
        # 全体への指定を守れない唯一のケースなので、plan_jobs が理由を表示する
    return info.audios[:1]


def audio_args(tracks: tuple[TrackPlan, ...]) -> list[str]:
    """選んだトラックぶんの -map と -c:a を組み立てる。

    添字は入力側のindexではなく「マップした並びの何番目か」。ffmpegの -c:a:N は
    出力側の音声ストリームを指すので、入力のa:2を1本目にマップしたら -c:a:0 になる。
    """
    single = len(tracks) == 1
    args = [arg for t in tracks for arg in ("-map", f"0:a:{t.source.index}")]
    for out_index, track in enumerate(tracks):
        # 1本だけなら添字を付けない。従来と同じコマンドラインになり、
        # 複数トラックを扱う新しい経路の外に影響が出ない
        at = "" if single else f":{out_index}"
        if track.codec == "copy":
            args += [f"-c:a{at}", "copy"]
        else:
            args += [f"-c:a{at}", track.codec,
                     f"-b:a{at}", f"{track.bitrate}k",
                     f"-ac{at}", str(track.channels)]
    if single:
        return args

    # 言語やタイトルのタグは黙っていてもコピーされる（mkv→mp4でも実測で保たれる）が、
    # 既定トラックの印だけはmuxerが勝手に立てる。MP4では実測で全トラックがdefault=1に
    # なり、どれを鳴らすかがプレイヤー任せになる。元がどれを既定にしていたかを見て、
    # 残したうちの1本にだけ付け直す。元の既定を落としたときは先頭を繰り上げる。
    default_at = next((i for i, t in enumerate(tracks) if t.source.default), 0)
    for out_index in range(len(tracks)):
        args += [f"-disposition:a:{out_index}", "default" if out_index == default_at else "0"]
    return args


def audio_note(tracks: tuple[TrackPlan, ...]) -> str:
    """結果行に出す音声の説明。1本なら従来どおりその1本の説明をそのまま返す。"""
    if len(tracks) == 1:
        return tracks[0].note
    return f"音声{len(tracks)}本: " + " / ".join(
        f"{t.source.label} {t.note}" for t in tracks)


def build_audio_args(info: MediaInfo, cfg: Config) -> AudioPlan:
    """音声まわり全体の計画。残すトラックを選び、1本ずつ扱いを決めてから組み立てる。"""
    selected = select_audio_tracks(info, cfg)
    if not selected:
        return AudioPlan(["-an"], "音声なし")
    tracks = tuple(plan_one_track(audio, info, cfg) for audio in selected)
    return AudioPlan(audio_args(tracks), audio_note(tracks), tracks)


def audio_selection_note(info: MediaInfo, plan: AudioPlan, cfg: Config) -> str | None:
    """指定どおりに選べなかったときの説明。守れたときはNone。"""
    if cfg.audio_tracks != "lang" or not info.audios:
        return None
    if any(t.source.language in cfg.audio_langs for t in plan.tracks):
        return None
    wanted = "/".join(LANGUAGE_NAMES.get(code, code) for code in cfg.audio_langs)
    return f"{wanted}の音声が無いので先頭（{info.audios[0].label}）を残します"


# ---------------------------------------------------------------------------
# 字幕
# ---------------------------------------------------------------------------


def build_subtitle_args(info: MediaInfo, suffix: str, cfg: Config) -> SubtitlePlan:
    """字幕は既定で持ち越す。入れ物に入らないものだけ落とす。

    MKVは何でもそのまま入る。MP4/WebMはテキスト字幕だけを変換して入れ、
    ビットマップ字幕（PGS・VobSub）は変換先が無いので落とすしかない。
    """
    def drop_all(reason: str) -> SubtitlePlan:
        # 空listではなく -sn を明示する。MKV出力ではffmpegの自動選択が
        # 字幕を拾い直してしまい、落としたつもりが残る
        return SubtitlePlan(["-sn"], dropped=info.subtitles,
                            note=reason if info.subtitles else "")

    if not info.subtitles:
        return SubtitlePlan([])
    if cfg.subtitles == "drop":
        return drop_all(f"字幕{len(info.subtitles)}本を落とします（--subtitles drop）")

    codec = SUBTITLE_CONTAINER_CODEC.get(suffix)
    if codec is None:
        return drop_all(f"字幕{len(info.subtitles)}本を落とします（{suffix} に入りません）")

    kept = tuple(s for s in info.subtitles if codec == "copy" or s.text_based)
    dropped = tuple(s for s in info.subtitles if s not in kept)
    if not kept:
        names = "/".join(sorted({(s.codec or "?") for s in dropped}))
        return drop_all(f"字幕{len(dropped)}本を落とします（{names} は {suffix} に入りません）")

    args = [arg for s in kept for arg in ("-map", f"0:s:{s.index}")] + ["-c:s", codec]
    if suffix == ".mkv":
        # ASSのフォントは添付ファイルとして入っている。連れて行かないと描画が崩れる
        args += ["-map", "0:t?"]
    # 字幕は「既定では表示しない」も意図のうちなので、元のフラグをそのまま写す。
    # MP4のdefaultはtkhdのenabledフラグなので、muxerが必ず先頭を立ててしまい
    # ここでは消せない（MKVは指定どおりになる）。forcedはどちらでも効く
    for out_index, sub in enumerate(kept):
        flags = [name for name, on in (("default", sub.default), ("forced", sub.forced)) if on]
        args += [f"-disposition:s:{out_index}", "+".join(flags) or "0"]

    note = ""
    if dropped:
        names = "/".join(sorted({(s.codec or "?") for s in dropped}))
        note = f"字幕{len(kept)}本を保持、{len(dropped)}本を破棄（{names} は {suffix} に入りません）"
    elif codec != "copy":
        note = f"字幕{len(kept)}本を{codec}へ変換"
    return SubtitlePlan(args, dropped, note)


def doomed_subtitles(info: MediaInfo, suffix: str) -> tuple[SubtitleInfo, ...]:
    """その入れ物に持ち越せない字幕。対話で「落としてよいか」を聞くために数える。"""
    codec = SUBTITLE_CONTAINER_CODEC.get(suffix)
    if codec is None:
        return info.subtitles
    if codec == "copy":
        return ()
    return tuple(s for s in info.subtitles if not s.text_based)


# ---------------------------------------------------------------------------
# 表示の整形
# ---------------------------------------------------------------------------

# 速度（実時間に対する倍率）をバーの色へ割り当てる。バーの描き方そのものは
# lib.progressbar が持っているので、ここにあるのは動画再圧縮に固有の対応付けだけ。


def band_color(speed: float) -> RGB:
    """その速度を表す色。波の変調は載せない（数字に添える用）。"""
    if speed >= RAINBOW_SPEED:
        return hue_rgb(0.0)
    return next(rgb for limit, rgb in reversed(SPEED_COLORS) if speed >= limit)


def bar_cell_color(speed: float, position: float, phase: float) -> RGB:
    """バー1マスの色。position はバー内の位置(0..1)、phase は経過秒。

    速度が上がるほど帯の色が変わり、最上位の帯ではレインボーが流れる。
    それ以外の帯では帯色の明度を波で揺らして、同じように流れて見せる。
    """
    if speed >= RAINBOW_SPEED:
        return rainbow_rgb(position, phase)
    return scale_rgb(band_color(speed), wave_level(position, phase))


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


class ProgressReporter(LiveLine):
    """エンコード中の進捗を1行にまとめて表示する。

    1行を書き換え続ける機構そのもの（再描画スレッド・行の消去・端末幅に応じた
    欄の配分）は lib.progressbar.LiveLine が持っている。ここで決めるのは
    「どの欄を、どんな文言で出すか」と、速度をどう色に割り当てるかだけ。

    総尺は解析時に分かっているので、全体に対する処理済み秒数で進捗率を出せる。
    -j で並列にしても行が混ざらないよう、本数ごとではなく全体を1行だけ書き換える。
    端末以外（パイプ・cron）・--verbose・--dry-run では何もしないので、
    ログの見た目は今までどおり。
    """

    def __init__(self, durations: dict[Path, float], layout: ResultLayout, enabled: bool,
                 sequential: bool) -> None:
        super().__init__(enabled=enabled)
        self.durations = durations                      # src -> 尺。1本ごとの進捗に使う
        self.total_duration = sum(durations.values())
        self.layout = layout
        self.sequential = sequential
        self.running: dict[Path, tuple[float, float]] = {}   # src -> (処理済み秒, 速度)
        self.done_duration = 0.0
        self.done_jobs = 0
        # 本と本の合間は走っているものが無く速度が0になる。バーの色がそのたびに
        # 最低速の帯（赤）へ落ちるのを避けるため、直近の速さを覚えておく。
        self.last_per_file = 0.0
        # 1本ごとのバーの状態。合間も直前の値を保つ（数フレームのことなので、
        # バーが一瞬消えるより繋がって見えるほうがよい）。尺が読めない入力に当たった
        # ときだけ None にして、割合の代わりに経過時間を出す。初期値は0（空のバー）。
        self.file_ratio: float | None = 0.0
        self.file_elapsed = 0.0

    @classmethod
    def for_jobs(cls, jobs: list[Job], cfg: Config, layout: ResultLayout) -> ProgressReporter:
        return cls(
            durations={job.info.path: job.info.duration for job in jobs},
            layout=layout,
            sequential=cfg.jobs <= 1,
            # ffmpegの進捗をそのまま流す--verboseや、行を書き換えられない端末以外では出さない
            enabled=cfg.progress and not cfg.verbose and not cfg.dry_run and sys.stderr.isatty(),
        )

    def update(self, src: Path, out_time: float, speed: float) -> None:
        """ffmpegから届いた1本分の進捗を反映する。"""
        with self.lock:
            self.running[src] = (out_time, speed)
            self.refresh()

    def finish(self, src: Path) -> None:
        """1本終わった分を完了側に移す。

        本数は数えない。エンコードを終えたワーカーがここを通ってから、本体が結果行を
        出すまでには間があり、その間にティックが走ると結果行より先にバーの番号が
        進んでしまうため（実際 [11/12] のバーの後に [10/12] の結果行が出ていた）。
        """
        with self.lock:
            self.running.pop(src, None)
            self.done_duration += self.durations.get(src, 0.0)

    def report(self, line: str, error: bool = False) -> None:
        """結果行を1本出す。

        呼び出しは1本につき1回なので、ここで本数を数える。こうするとバーの番号は
        「最後に出した結果行の次」に必ず一致し、追い越しが起きない。
        """
        with self.lock:
            self.done_jobs += 1
            # 1本ごとのバーも同じ場所で次の本へ送る。カウンタと別の場所で戻すと、
            # 合間に「[2/3] なのにバーは前の本の100%」という食い違いが出る
            # （次のffmpegが起動して最初の進捗を出すまで1秒近くある）。
            self.file_ratio, self.file_elapsed = 0.0, 0.0
            super().report(line, error)

    def cell_color(self, slot: BarSlot, position: float, phase: float) -> RGB:
        """速度に応じた光沢をバーに流す。"""
        return bar_cell_color(slot.intensity, position, phase)

    def _paint(self, text: str, rgb: RGB) -> str:
        return paint(text, rgb, self.stream) if self.color else text

    def parts(self) -> list[str | BarSlot]:
        """1行に並べる欄。逐次と並行で見せ方を変える。"""
        processed = self.done_duration + sum(t for t, _ in self.running.values())
        running = len(self.running)
        # 合算スループット。残り時間はこれで割る（全体が何倍速で進んでいるか）
        speed = sum(s for _, s in self.running.values())
        # 1本あたりの速さ。色はこちらで決める。合算のままだと -j 3 で 6x×3=18x となり、
        # 並行数を上げただけで最上位帯へ張り付いて色が情報を持たなくなるため。
        per_file = speed / running if running else 0.0
        if per_file > 0:
            self.last_per_file = per_file
        return (self._file_parts(processed, speed) if self.sequential
                else self._batch_parts(processed, speed, per_file, running))

    def _file_parts(self, processed: float, speed: float) -> list[str | BarSlot]:
        """逐次実行（-j 1）の1行。バーは「今の1本」、全体の進み具合は数字で添える。

        全体バーは本数が増えるほど動かなくなる。20マスに31本なら1本あたり0.65マスで、
        3分のファイルを1本まるごと変換してもマスが動かないことがあり、目で追う対象と
        して機能しない。そこでバーは毎回フルスイングする「今の1本」に充て、
        「あと何分で全部終わるか」は数字（全体% と 残り）で持つ。
        """
        # ファイル名は走っている間だけ出す。合間も直前の名前を出し続けると、カウンタが
        # 次の本へ進んだ後に前の本の名前が残り（[2/3] ... k1.mp4）、次のffmpegが起動して
        # 最初の進捗を出すまでの1秒近く、番号と名前が食い違って見えるため。
        name = ""
        if self.running:
            src, (out_time, _) = next(iter(self.running.items()))
            duration = self.durations.get(src, 0.0)
            self.file_ratio = min(out_time / duration, 1.0) if duration > 0 else None
            self.file_elapsed = out_time
            name = src.name

        # いま処理している本が何本目か。行末にファイル名が並ぶので、番号もそのファイルを
        # 指していないと「f2.mov が1本目」と読めてしまう。この番号は、その本が終わった
        # ときに出る結果行の番号と必ず一致する。本と本の合間も次の1本の番号のまま
        # 据え置く（完了本数へ戻すと、合間だけ表示幅が変わって行が横にずれるため）。
        parts: list[str | BarSlot] = [self.layout.counter(min(self.done_jobs + 1,
                                                              self.layout.total))]
        if self.file_ratio is None:
            # 尺が読めなかった入力。割合が出せないので経過時間で代える
            parts.append(f"{clock(self.file_elapsed)} 処理済み")
        else:
            parts.append(BarSlot(self.file_ratio, self.last_per_file))
            parts.append(f"{self.file_ratio:4.0%}")
        if speed > 0:
            # 数字にも帯の色を乗せて、バーの色が何を表しているのかを結び付ける
            parts.append(self._paint(f"{speed:>5.3g}x", band_color(speed)))
        if self.total_duration > 0:
            parts.append(f"全体 {min(processed / self.total_duration, 1.0):4.0%}")
            if speed > 0:
                parts.append(f"残り {clock((self.total_duration - processed) / speed)}")
        if name:
            parts.append(truncate_display(name, BAR_NAME_MAX_WIDTH))
        return parts

    def _batch_parts(self, processed: float, speed: float, per_file: float,
                     running: int) -> list[str | BarSlot]:
        """並行実行（-j 2以上）の1行。バーは全体の進み具合。

        走っている本が複数あると「今の1本」を指せないので、バーは全体に充てる。
        番号も先読みできない。結果行の番号は完了順に振られるので、走っている1本が
        次に終わるとは限らず、先に出した番号が別のファイルに付いてしまう。
        特定の1本を指せない以上、完了本数だと分かる書き方にする。
        """
        parts: list[str | BarSlot] = [self.layout.done_counter(self.done_jobs)]
        if self.total_duration > 0:
            ratio = min(processed / self.total_duration, 1.0)
            parts.append(f"{ratio:4.0%}")
            parts.append(BarSlot(ratio, per_file or self.last_per_file))
            parts.append(f"{clock(processed)}/{clock(self.total_duration)}")
            if speed > 0:
                parts.append(f"残り {clock((self.total_duration - processed) / speed)}")
        else:
            parts.append(f"{clock(processed)} 処理済み")
        if speed > 0:
            # 「1本あたり / 本数」で出す。色と同じ数字を見せないと、なぜその色なのかが
            # 分からなくなる。合算値は残り時間に現れている。
            text = (f"{per_file:>5.3g}x / {running}" if running > 1
                    else f"{speed:>5.3g}x")
            parts.append(self._paint(text, band_color(per_file)))
        if running == 1:
            parts.append(truncate_display(next(iter(self.running)).name, BAR_NAME_MAX_WIDTH))
        return parts


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


def build_encode_command(info: MediaInfo, tmp: Path, plan: AudioPlan, subs: SubtitlePlan,
                         cfg: Config, with_progress: bool) -> list[str]:
    """1本分のffmpegコマンドライン。出力は書きかけの一時ファイル。"""
    cmd = [
        "ffmpeg", "-y", "-nostdin",
        *(["-v", "info", "-stats"] if cfg.verbose else ["-v", "error", "-nostats"]),
        *(["-progress", "pipe:1"] if with_progress else []),
        "-i", str(info.path),
        "-map", "0:v:0",
        # 既定と同じ挙動だが、-map を明示している以上ここも明示しておく。
        # 映像と音声だけを選んでいるように読めて、実はチャプターも来ている、を避ける
        "-map_chapters", "0",
        *build_video_args(info, cfg),
    ]
    # 音声なしは build_audio_args が ["-an"] として返している
    cmd += plan.args
    cmd += subs.args
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
    cmd = build_encode_command(info, tmp, job.plan, job.subs, cfg, progress.enabled)

    def subtitle_line(indent: str) -> str:
        return f"\n{indent}subtitle: {job.subs.note}" if job.subs.note else ""

    if cfg.dry_run:
        destination = f"\n          → {dst.name}（元はゴミ箱へ）" if cfg.replace else ""
        print(f"[dry-run] {src.name}\n          audio: {job.plan.note}"
              f"{subtitle_line(' ' * 10)}{destination}"
              f"\n          {shlex.join(cmd)}", file=sys.stderr)
        return Result(src, dst, True, "dry-run", info.size, 0)

    dst.parent.mkdir(parents=True, exist_ok=True)
    if cfg.verbose:
        print(f"--- {src.name}\n    audio: {job.plan.note}"
              f"{subtitle_line(' ' * 4)}\n    {shlex.join(cmd)}", flush=True, file=sys.stderr)
    returncode, stderr = run_encoder(cmd, src, cfg, progress)
    progress.finish(src)

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


def collect_inputs(roots: Sequence[Path], recursive: bool, outdir: Path | None) -> list[Path]:
    """入力を集める。書きかけの一時ファイルと、入力ツリーの内側の出力先は除く。

    `ffmpeg-convert.py . -o compressed` のように出力先を入力の内側に置くのは
    自然な使い方だが、素朴に走査すると2回目の実行で出力済みファイルを入力として
    拾い、再圧縮してしまう。中断時に残る *.part.mp4 は出力先の外（--replace なら
    元ファイルの隣）にも生まれるので、拡張子で別に弾く。

    出力先はパスの文字列ではなくディレクトリの実体（st_dev と st_ino）で見分ける。
    APFSは大文字小文字を区別しないので、`-o AV1` と av1/ は同じディレクトリだが、
    文字列で比べると別物と判定して出力済みファイルを拾ってしまう。
    今回の出力先でなくても、.ffmpeg-convert があるディレクトリは別の -o の
    出力先とみなして外す（is_other_output）。

    Config ではなく素の3つを受けるのは、対話より前――Configが組み上がる前に
    呼ぶため。何に依存しているかを引数で明示しておく。
    """
    outdir_id = directory_identity(outdir) if outdir is not None else None

    def is_outdir(d: Path) -> bool:
        return outdir_id is not None and directory_identity(d) == outdir_id

    found: list[Path] = []
    for root in roots:
        if root.is_file():
            found.append(root)
            continue
        if not root.is_dir():
            continue
        for dirpath, dirnames, filenames in root.walk():
            if is_outdir(dirpath):
                # 入力として出力先そのものを渡された場合
                dirnames.clear()
                continue
            # 出力先の下へは降りない。見るのは1段につき stat 1回で済む
            dirnames[:] = [] if not recursive else [
                d for d in dirnames
                if not is_outdir(dirpath / d) and not is_other_output(dirpath / d, root)]
            found += [p for name in filenames
                      if (p := dirpath / name).suffix.lower() in VIDEO_SUFFIXES
                      and ".part" not in p.suffixes and p.is_file()]
    return sorted(set(found))


def is_other_output(directory: Path, root: Path) -> bool:
    """別の -o で作った出力先か。そうなら走査から外したことを知らせる。

    `. -o hevc && . -o av1` のように同じ入力から出力先を変えて作ると、2回目は
    hevc/ の変換済みファイルまで入力として拾ってしまう。設定ファイルがある
    ディレクトリは出力先の印とみなして外す。黙って外すと「入れたはずの動画が
    変換されない」の原因が分からないので、外すたびに1行出す。

    起点として直接渡されたディレクトリは対象外（呼び出し側が起点を渡さない）。
    明示的に指定されたものまで外すのはやりすぎなので。
    """
    if not (directory / SETTINGS_FILENAME).is_file():
        return False
    print(f"スキップ: {directory.relative_to(root)}/"
          f"（{SETTINGS_FILENAME} があるので別の変換の出力先とみなします）", file=sys.stderr)
    return True


def directory_identity(path: Path) -> tuple[int, int] | None:
    """ディレクトリの実体を表す (st_dev, st_ino)。まだ無いディレクトリは None。"""
    try:
        st = path.stat()
    except OSError:
        return None
    return (st.st_dev, st.st_ino)


# 末尾の [ ] を「設定の要約」と見なして剥がすための語彙。自分が書いた名前
# （[av1 720p crf35]）だけでなく、他所で付けられた [1080p x265] 風の名前も剥がせるよう、
# 同じものを指す別名も入れてある。
ENCODER_NAME_ALIASES = frozenset({"x264", "avc", "x265", "h265", "svtav1", "vp8", "vp9"})

# -t/--tune に渡せる値（x264/x265）。設定の要約に現れうるので語彙に含める。
TUNE_WORDS = frozenset({"animation", "film", "grain", "stillimage",
                        "fastdecode", "zerolatency", "psnr", "ssim"})

# 「720p」「crf35」のような、語彙に並べられない形の語。
PARAMETER_TOKEN_RE = re.compile(r"\d{3,4}p|crf\d+")

# 名前の末尾にある [ ]。中に [ ] を含まない、いちばん外側の一組だけを捉える。
TRAILING_BRACKET_RE = re.compile(r"\s*\[([^\[\]]*)\]$")


def is_parameter_token(token: str) -> bool:
    """[ ] の中の1語が、設定の要約として書かれたものに見えるか。"""
    word = token.lower()
    return (word in ENCODER_LIBRARIES or word in ENCODER_NAME_ALIASES
            or word in TUNE_WORDS or word == "lecture"
            or PARAMETER_TOKEN_RE.fullmatch(word) is not None)


def strip_parameter_suffix(stem: str) -> str:
    """元名の末尾に付いている設定の要約を落とす。

    一度変換したものを設定を変えて変換し直すと「動画 [1080p h264] [av1 720p crf35]」と
    積み重なってしまうので、付け替えられるように剥がす。

    剥がすのは末尾の [ ] が設定の語だけで出来ているときに限る。アニメの配布名に付く
    [A1B2C3D4]（CRC）や「[完]」のような、中身を表す [ ] は残す。[1080p][h264] のように
    分かれていることもあるので、設定に見える限り繰り返し剥がす。
    """
    while (match := TRAILING_BRACKET_RE.search(stem)) is not None:
        tokens = [t for t in re.split(r"[\s,]+", match.group(1)) if t]
        if not tokens or not all(is_parameter_token(t) for t in tokens):
            break
        rest = stem[:match.start()].rstrip()
        if not rest:
            # 名前が [ ] だけで出来ている場合。剥がすと名前が消えるので残す
            break
        stem = rest
    return stem


def parameter_suffix(info: MediaInfo, cfg: Config) -> str:
    """出力名に添える設定の要約。元ファイルと並べても、設定を変えて作り直しても区別できる。

    「元名 [av1 720p crf35].webm」の形で、コーデック・解像度・CRFの順に並べる。
    画質は段階名ではなくCRFの実値を書く。段階名はコーデックと素材で指す値が変わり
    （同じ portable でも x265なら30、AV1なら35、--lecture ならまた別）、名前を見ても
    何をしたのか分からないため。CRFは常に書くので、既定のまま変換した本も名前から
    設定を読み取れる。
    """
    parts = [ENCODER_NAMES[cfg.encoder]]
    # 元より小さい指定でなければ縮小は起きないので、そのときは名前にも出さない。
    # 判定は scale_filter に任せて「名前と中身が食い違う」ことを防ぐ。
    if scale_filter(info, cfg.size):
        parts.append(f"{cfg.size}p")
    parts.append(f"crf{cfg.crf}")
    if cfg.tune:
        parts.append(cfg.tune)
    if cfg.lecture:
        parts.append("lecture")
    return " ".join(parts)


def destination_for(info: MediaInfo, suffix: str, cfg: Config) -> Path:
    """出力パスを決める。

    単発ファイルの変換では「元名 [hevc 720p crf28].mp4」のように設定を名前に書く。
    元ファイルの隣に置いても区別でき、設定を変えて作り直しても衝突しないため。
    元名に既に設定が書いてあれば、積み重ねずに付け替える。
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
        stem = strip_parameter_suffix(src.stem)
        return parent / f"{stem} [{parameter_suffix(info, cfg)}]{suffix}"
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


def settings_path(args: argparse.Namespace) -> Path | None:
    """設定ファイルを読み書きする場所。-o でディレクトリを指定したときだけある。

    -o を付けない実行（既定の compressed/ や元と同じ場所）と、-o out.mp4 のように
    出力ファイル名を指定した実行は対象外。後者で out.mp4 の隣に設定ファイルを
    置くと、たまたま同じ場所に書いた別の変換にまで効いてしまう。
    """
    if args.output is None or args.output_file is not None or args.outdir is None:
        return None
    return args.outdir / SETTINGS_FILENAME


def load_settings(parser: argparse.ArgumentParser, path: Path) -> dict[str, object]:
    """設定ファイルを読んで検証する。壊れていたら黙って無視せずエラーにする。"""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        parser.error(f"設定ファイルを読めません: {path}（{exc}）")
    if not isinstance(data, dict):
        parser.error(f"設定ファイルの形式が違います: {path}")

    settings: dict[str, object] = {}
    for key, value in data.items():
        if key == "version":
            continue
        validator = SETTINGS_VALIDATORS.get(key)
        if validator is None:
            # 新しい版で増えたキーかもしれないので、止めずに知らせるだけにする
            print(f"注意: 設定ファイルの {key} は知らない項目なので無視します（{path}）", file=sys.stderr)
            continue
        if not validator(value):
            parser.error(f"設定ファイルの {key} の値が不正です: {value!r}（{path}）")
        settings[key] = value
    return settings


def is_unset_on_cli(args: argparse.Namespace, key: str) -> bool:
    return getattr(args, key) == SETTINGS_UNSET_VALUES.get(key)


def apply_settings(args: argparse.Namespace, settings: dict[str, object]) -> None:
    """保存した設定のうち、コマンドラインで指定されなかったものを args に入れる。

    組になった設定（SETTINGS_LINKED_GROUPS）は、どれか1つでも指定されていたら
    組ごと保存した値を使わない。
    """
    explicit = {key for key in SETTINGS_VALIDATORS if not is_unset_on_cli(args, key)}
    blocked = explicit.union(*(group for group in SETTINGS_LINKED_GROUPS if group & explicit))
    for key, value in settings.items():
        if key in blocked:
            continue
        setattr(args, key, tuple(value) if key == "audio_lang" else value)
    # parse_args で --audio-lang に対して行うのと同じ補完。手で書いた設定ファイルに
    # audio_lang だけがある場合に、言語を指定したのに先頭が残る、を防ぐ
    if args.audio_lang and args.audio_tracks is None:
        args.audio_tracks = "lang"


def settings_to_save(values: dict[str, object]) -> dict[str, object]:
    """保存する中身。未指定（None）の項目は書かない。"""
    kept = {key: list(value) if isinstance(value, tuple) else value
            for key, value in values.items() if value is not None}
    assert set(kept) <= set(SETTINGS_VALIDATORS), set(kept) - set(SETTINGS_VALIDATORS)
    return {"version": SETTINGS_VERSION, **kept}


def save_settings(path: Path, values: dict[str, object]) -> None:
    """設定ファイルを書く。出力先ディレクトリはまだ無いこともあるので作る。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings_to_save(values), ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


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

    if args.audio_lang is not None and args.audio_tracks not in (None, "lang"):
        parser.error(f"--audio-lang は --audio-tracks {args.audio_tracks} と併用できません")
    if args.audio_tracks == "lang" and args.audio_lang is None:
        parser.error("--audio-tracks lang には --audio-lang で言語の指定が要ります")


def parse_languages(value: str) -> tuple[str, ...]:
    """--audio-lang をコードの並びに直す。'jpn,eng' でも 'jpn eng' でも受ける。"""
    codes = tuple(code for code in re.split(r"[,\s]+", value.strip().lower()) if code)
    if not codes:
        raise argparse.ArgumentTypeError("言語コードを1つ以上指定してください（例: jpn,eng）")
    return codes


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


def parse_nice(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"整数で指定してください: {text}") from None
    if not 0 <= value <= 19:
        raise argparse.ArgumentTypeError(f"0〜19で指定してください: {value}")
    return value


def lower_priority(niceness: int) -> None:
    """自プロセスの nice 値を niceness まで上げる。子の ffmpeg/ffprobe も引き継ぐ。

    一般ユーザーは優先度を上げ戻せないので、既に niceness 以上なら何もしない
    （nice -n 19 で起動された場合に 0 へ戻そうとして失敗しないように）。
    サンドボックス等で変更を拒まれても、変換自体は止めずに警告だけ出す。
    """
    try:
        if niceness > os.getpriority(os.PRIO_PROCESS, 0):
            os.setpriority(os.PRIO_PROCESS, 0, niceness)
    except OSError as e:
        print(f"警告: 優先度を nice {niceness} に下げられませんでした（{e.strerror}）",
              file=sys.stderr)


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="動画をH.264/HEVC/AV1で再圧縮する",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("inputs", nargs="+", type=Path, help="入力ファイルまたはディレクトリ")
    p.add_argument("-o", "--output", type=Path, default=None,
                   help="出力先ディレクトリ。単発ファイルの変換時は拡張子付きのファイル名も"
                        "受け取る（既定: ディレクトリ入力なら compressed/、単発ファイルなら"
                        f"元と同じ場所）。ディレクトリに {SETTINGS_FILENAME} があれば"
                        "その設定を使う")
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
    p.add_argument("--audio-mode", choices=AUDIO_MODE_OPTIONS, default="auto",
                   help=f"auto=非可逆{LOSSY_COPY_MAX_BITRATE // 1000}k以下ならコピー、可逆なら圧縮。"
                        "prefer-copy=可能な限りコピー（MP4で再生できないコーデックのみAAC化）")
    p.add_argument("--audio-codec", choices=AUDIO_CODEC_OPTIONS, default="auto",
                   help="auto=--av1ならopus、それ以外はaac（--container mp4 指定時はaac）")
    p.add_argument("--container", choices=CONTAINER_OPTIONS, default="auto",
                   help="出力コンテナ。auto=AV1+Opusならwebm、他のOpusならmkv、それ以外はmp4")
    p.add_argument("--audio-bitrate", type=int, default=None,
                   help="ステレオ再エンコード時のkbps（既定: aac 128 / opus 96）")
    p.add_argument("--mono-bitrate", type=int, default=None,
                   help="モノラル再エンコード時のkbps（既定: aac 128 / opus 64）")
    p.add_argument("--audio-tracks", choices=AUDIO_TRACK_OPTIONS,
                   default=argparse.SUPPRESS,
                   help="複数音声があるときにどれを残すか。first=先頭のみ（既定）、all=すべて。"
                        "残す本数が増えると出力も大きくなるので --replace では"
                        "「元より大きい」として置き換えない本が増える")
    p.add_argument("--audio-lang", type=parse_languages, default=None, metavar="CODES",
                   help="残す音声の言語（jpn,eng のように複数可）。--audio-tracks lang と同じ。"
                        "指定した言語が無いファイルは先頭のトラックを残す")
    p.add_argument("--subtitles", choices=SUBTITLE_OPTIONS, default="keep",
                   help="字幕を持ち越すか（既定: keep）。入れ物に入らない字幕は落とす")
    p.add_argument("--no-subtitles", dest="subtitles", action="store_const", const="drop",
                   help="字幕を落とす（--subtitles drop と同じ）")
    p.add_argument("-j", "--jobs", type=int, default=1, help="並列実行数")
    p.add_argument("--nice", type=parse_nice, default=DEFAULT_NICE, metavar="N",
                   help="この nice 値（0〜19、大きいほど低優先度）で走らせる。0 で下げない")
    p.add_argument("--overwrite", action="store_true",
                   help="出力が既にあっても上書きする（既定はスキップ）")
    p.add_argument("--replace", action="store_true",
                   help="変換結果で元ファイルを置き換える（元はゴミ箱へ / -o とは併用不可）")
    p.add_argument("--no-interactive", dest="interactive", action="store_false",
                   help="未指定のオプションを聞かず既定で実行する（端末以外では常にこの挙動）")
    p.add_argument("--no-saved-settings", dest="saved_settings", action="store_false",
                   help=f"-o 先の {SETTINGS_FILENAME} を読まずに実行する"
                        "（端末実行なら改めて質問し、保存し直せる）")
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
    args.audio_tracks = getattr(args, "audio_tracks", None)
    if args.audio_lang and args.audio_tracks is None:
        args.audio_tracks = "lang"
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

    # 保存した設定は、組み合わせの検証より前に入れる。保存した --apple と今回の
    # --audio-codec opus のような矛盾も、コマンドラインで両方書いたときと同じく弾く。
    args.settings_path = settings_path(args)
    args.settings_loaded = False
    if args.saved_settings and args.settings_path is not None and args.settings_path.is_file():
        apply_settings(args, load_settings(p, args.settings_path))
        args.settings_loaded = True
        # 自動で使うと決めた以上、残りも質問しない（Apple互換や字幕の質問が
        # 毎回出ては、保存した意味がない）
        args.interactive = False
        print(f"保存済みの設定を使います: {args.settings_path}"
              "（使わないときは --no-saved-settings）", file=sys.stderr)

    validate_combinations(p, args)
    return args


# ---------------------------------------------------------------------------
# 対話による設定の確定
# ---------------------------------------------------------------------------


def prompt_audio_tracks(scan: list[MediaInfo]) -> tuple[str, tuple[str, ...]]:
    """複数音声があるファイルについて、どれを残すか聞く。

    選択肢は実データから作る。入っていない言語を並べても選びようがない。
    """
    multi = [info for info in scan if len(info.audios) > 1]
    counts: dict[str, int] = {}
    for info in multi:
        for code in {a.language for a in info.audios if a.language}:
            counts[code] = counts.get(code, 0) + 1

    options = [("first", f"先頭の1本だけ — 今までどおり（{len(multi)}本が複数音声）")]
    for code, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        name = LANGUAGE_NAMES.get(code, code)
        options.append((f"lang:{code}", f"{name} — {count}本のファイルに入っています"))
    options.append(("all", "すべて残す — 入れ物が対応していれば全トラックを持ち越す"))

    chosen = prompt_choice(
        f"音声が複数あるファイルが {len(multi)} 本あります。どれを残しますか",
        options, "first")
    if chosen.startswith("lang:"):
        return "lang", (chosen.split(":", 1)[1],)
    return chosen, ()


def prompt_subtitle_drop(doomed: list[tuple[MediaInfo, tuple[SubtitleInfo, ...]]],
                         suffix: str, may_switch: bool) -> str:
    """入れ物に入らない字幕があるとき、どうするか聞く。戻り値は "drop" か "mkv"。"""
    names = "/".join(sorted({(s.codec or "?") for _, subs in doomed for s in subs}))
    options = [("drop", "字幕を落として変換する")]
    if may_switch:
        options.append(("mkv", "入れ物をMKVにして字幕を残す"))
    options.append(("abort", "中止する"))

    chosen = prompt_choice(
        f"字幕が {len(doomed)} 本のファイルで落ちます"
        f"（{names} は {suffix} に入りません）。どうしますか",
        options, "drop")
    if chosen == "abort":
        print("中断しました", file=sys.stderr)
        raise SystemExit(130)
    return chosen


def offer_to_save_settings(path: Path, values: dict[str, object]) -> bool:
    """今回の設定を -o 先に保存するか聞く。保存したら True。"""
    question = (f"今回の設定で {path} を上書きしますか" if path.exists()
                else "今回の設定を保存しますか")
    if not confirm(f"\n{question}（次回同じ -o を指定すると質問せずに使います）", default=True):
        return False
    try:
        save_settings(path, values)
    except OSError as exc:
        # 保存に失敗しても変換そのものは続けられる
        print(f"設定を保存できませんでした: {path}（{exc}）", file=sys.stderr)
        return False
    print(f"設定を保存しました: {path}", file=sys.stderr)
    return True


def resolve_options(args: argparse.Namespace, scan: list[MediaInfo]) -> Config:
    """未指定のオプションを対話か既定値で埋め、実行設定を組み立てる。

    端末から人が実行したときだけ質問する。パイプ・cron・--no-interactive では
    黙って既定（HEVC + MP4）に落ちるので、バッチ実行の挙動は変わらない。

    scan は解析済みの入力。音声トラックと字幕の質問は、実際に何が入っているかを
    見てからでないと出せない（入っていないものを聞いても仕方がない）ため受け取る。
    """
    interactive = args.interactive and stdio_is_interactive()
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
    # 音声トラックの選択。複数持つファイルが1本も無ければ聞く意味がない
    audio_tracks, audio_langs = args.audio_tracks, tuple(args.audio_lang or ())
    if (interactive and audio_tracks is None
            and max((len(info.audios) for info in scan), default=0) >= 2):
        audio_tracks, audio_langs = prompt_audio_tracks(scan)
        if audio_tracks == "all":
            answered.append("--audio-tracks all")
        elif audio_tracks == "lang":
            answered.append(f"--audio-lang {','.join(audio_langs)}")
    if audio_tracks is None:
        audio_tracks = "first"

    # 字幕。ここまでで入れ物が決まるので、落ちるものがあるかを先に見積もれる。
    # 出力の拡張子は設定が固まれば全ファイル共通になる（Opusを使うかどうかだけで
    # 決まり、それは cfg の関数）ので、ファイルごとに聞く必要はない
    subtitles = args.subtitles
    if interactive and subtitles == "keep":
        suffix = predicted_suffix(container, audio_codec, encoder)
        doomed = [(info, subs) for info in scan
                  if (subs := doomed_subtitles(info, suffix))]
        if doomed:
            # 入れ物を明示されているときに黙って差し替えるのはやりすぎなので、
            # MKVへの切り替えは自分で決めた（auto の）ときだけ選ばせる
            may_switch = args.container == "auto" and args.output_file is None and not apple
            if prompt_subtitle_drop(doomed, suffix, may_switch) == "mkv":
                container = "mkv"
                answered.append("--container mkv")

    saved = interactive and args.settings_path is not None and offer_to_save_settings(
        args.settings_path, {
            "content": content, "size": size, "apple": apple, "encoder": encoder,
            # --crf を明示されていれば -q は使われていない
            "quality": quality if args.crf is None else None, "crf": args.crf,
            "tune": args.tune, "preset": args.preset, "gop_seconds": args.gop_seconds,
            "audio_mode": args.audio_mode, "audio_codec": audio_codec, "container": container,
            "audio_bitrate": args.audio_bitrate, "mono_bitrate": args.mono_bitrate,
            "audio_tracks": audio_tracks, "audio_lang": audio_langs or None,
            "subtitles": subtitles,
        })
    if answered and not saved:
        print(f"（次回から {' '.join(answered)} を付けるか、--no-interactive で質問を省けます）", file=sys.stderr)

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
        crf=args.crf if args.crf is not None else crf_table(lecture, encoder)[quality],
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
        audio_tracks=audio_tracks,
        audio_langs=audio_langs,
        subtitles=subtitles,
        jobs=args.jobs,
        dry_run=args.dry_run,
        verbose=args.verbose,
        progress=args.progress,
    )


# ---------------------------------------------------------------------------
# 全体の進行
# ---------------------------------------------------------------------------


def announce_inputs(args: argparse.Namespace, total: int) -> None:
    """解析に入る前に、どこへ書くつもりなのかを伝える。

    対話より前に呼ぶので Config はまだ無い。ここで参照する3つは
    argparse の時点で確定している。
    """
    if args.replace:
        print("出力先: 元ファイルと同じ場所（元ファイルはゴミ箱へ移します）", file=sys.stderr)
    else:
        print(f"出力先: {args.output_file or args.outdir or args.inputs[0].parent}"
              "（元ファイルは変更しません）", file=sys.stderr)
    print(f"{total} 本を解析中…", file=sys.stderr)


def announce_settings(cfg: Config) -> None:
    """設定が固まった時点で、黙っていられない組み合わせだけ警告する。"""
    if cfg.apple and cfg.encoder == "libsvtav1":
        print("注意: AV1はA17 Pro / M3世代以降のApple機でのみ再生できます"
              "（M1・M2世代では再生できません）", file=sys.stderr)


def describe_source(info: MediaInfo) -> str:
    """解析結果の1行。映像 / 音声 / 字幕 / サイズ の順に並べる。"""
    audio_desc = "音声なし"
    if info.audios:
        first = info.audios[0]
        kbps = f"{first.bitrate // 1000}k" if first.bitrate else "?"
        audio_desc = f"{first.codec} {first.channels}ch {kbps}"
        if len(info.audios) > 1:
            audio_desc += f" 他{len(info.audios) - 1}本"
    parts = [f"{info.width}x{info.height} {info.fps:.3g}fps {info.video_codec}", audio_desc]
    if info.subtitles:
        parts.append(f"字幕{len(info.subtitles)}本")
    parts.append(human(info.size))
    return f"  {info.path.name}: {' / '.join(parts)}"


def summarize_scan(scan: list[MediaInfo]) -> str:
    """本数が多いときの集計行。1本ずつ出すと質問が画面外へ流れるため。"""
    multi_audio = sum(1 for i in scan if len(i.audios) > 1)
    with_subs = sum(1 for i in scan if i.subtitles)
    parts = [f"{len(scan)} 本"]
    if multi_audio:
        parts.append(f"音声2本以上: {multi_audio} 本")
    if with_subs:
        parts.append(f"字幕あり: {with_subs} 本")
    parts.append(human(sum(i.size for i in scan)))
    return f"  {' / '.join(parts)}"


def scan_inputs(sources: list[Path]) -> tuple[list[MediaInfo], int]:
    """入力をまとめて解析する。(解析できたもの, 解析できなかった本数) を返す。

    対話より前に走るので、ここでの待ち時間はそのまま最初の質問までの待ち時間になる。
    ffprobeはプロセスを待つだけでGILを握らないため、スレッドで並べる。
    結果は投入順に回収して、表示順と終了コードを実行ごとに揺らさない。
    """
    scan: list[MediaInfo] = []
    failed = 0
    try:
        with ThreadPoolExecutor(max_workers=PROBE_WORKERS) as pool:
            futures = [(src, pool.submit(probe, src)) for src in sources]
            for src, future in futures:
                try:
                    scan.append(future.result())
                except (ProbeError, json.JSONDecodeError) as exc:
                    print(status_line("NG", NG_RGB, f"{src.name}: {exc}", sys.stderr), file=sys.stderr)
                    failed += 1
    except KeyboardInterrupt:
        # 拾わないと ThreadPoolExecutor の後始末で全本の完了を待たされる
        print("\n中断しました", file=sys.stderr)
        raise SystemExit(130)

    if len(scan) > SCAN_DETAIL_MAX:
        print(summarize_scan(scan), file=sys.stderr)
    else:
        for info in scan:
            print(describe_source(info), file=sys.stderr)
    return scan, failed


def plan_jobs(scan: list[MediaInfo], cfg: Config) -> tuple[list[Job], int]:
    """解析済みの1本ずつについて変換内容を決める。

    (変換する仕事の一覧, 組み合わせの都合で処理できなかった本数) を返す。
    後者は終了コードに出す。既に出力がある等で意図どおり飛ばした分は数えない。
    """
    jobs: list[Job] = []
    skipped = 0
    for info in scan:
        src = info.path
        # コンテナは音声の計画で決まる（Opusを使うならMKV）ので、先に立てる
        plan = build_audio_args(info, cfg)
        suffix = container_suffix(plan, cfg)
        conflict = container_audio_conflict(plan, suffix, cfg)
        if conflict:
            print(status_line("NG", NG_RGB, f"{src.name}: {conflict}", sys.stderr), file=sys.stderr)
            skipped += 1
            continue
        dst = destination_for(info, suffix, cfg)
        # --replace で拡張子が変わらないときは dst が src そのもの。それは想定どおり
        # 大文字小文字を区別しないAPFSでは hello.MP4 と hello.mp4 は同じファイル。
        # 文字列で比べると別物に見えるので、inode で確かめる
        same_path = dst.exists() and dst.samefile(src)
        if same_path and not cfg.replace:
            print(status_line("skip", None, f"{src.name}（出力先が入力と同一）"), file=sys.stderr)
            continue
        if dst.exists() and not same_path and not cfg.overwrite:
            print(status_line("skip", None, f"{src.name}（出力が既にあります。作り直すなら --overwrite）"), file=sys.stderr)
            continue

        # ここから先は「変換はするが、そのまま通すと黙って欠けるもの」の報告。
        # 対話はしない（ファイルごとに聞くと本数ぶん出るし、-j や非TTYで詰まる）
        subs = build_subtitle_args(info, suffix, cfg)
        for note in (audio_selection_note(info, plan, cfg),
                     container_audio_warning(plan, suffix),
                     subs.note if subs.dropped else None):
            if note:
                print(status_line("注意", NOTE_RGB, f"{src.name}: {note}", sys.stderr), file=sys.stderr)

        jobs.append(Job(info, dst, plan, subs))
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
    print(f"\n{len(jobs)} 本を {settings_summary(cfg)} で圧縮します（並列 {cfg.jobs}）", file=sys.stderr)
    results: list[Result] = []
    with (ProgressReporter.for_jobs(jobs, cfg, layout) as progress,
          ThreadPoolExecutor(max_workers=max(cfg.jobs, 1)) as pool):
        futures = [pool.submit(encode, job, cfg, progress) for job in jobs]
        for done, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            results.append(result)
            prefix = layout.prefix(done, result.src.name)
            if not result.ok:
                progress.report(f"{prefix} {paint('NG', NG_RGB, sys.stderr)} {result.message}", error=True)
            elif result.kept:
                progress.report(f"{prefix} {result.message}")
            elif not cfg.dry_run:
                progress.report(f"{prefix} {size_change(result.src_size, result.dst_size, stream=sys.stderr)}"
                                f" / {result.message}")
    return results


def report(results: list[Result], skipped: int, multi_audio: bool,
           layout: ResultLayout) -> int:
    """結果をまとめて、終了コードを返す。"""
    ok = [r for r in results if r.ok]
    kept = [r for r in ok if r.kept]
    src_total = sum(r.src_size for r in ok)
    dst_total = sum(r.dst_size for r in ok)
    print(f"\n完了 {len(ok)}/{len(results)} 本", file=sys.stderr)
    if kept:
        print(f"うち {len(kept)} 本は元より大きくなったため置き換えていません", file=sys.stderr)
        if multi_audio:
            # 音声を2本以上残せばその分は太る。設定どおりの結果であって失敗ではない
            print("（音声を複数残すぶん出力は大きくなります。"
                  "--audio-tracks first なら1本だけ残します）", file=sys.stderr)
    if src_total:
        # 結果行と同じ欄に合計を置く
        print(f"{layout.label('合計')} "
              f"{size_change(src_total, dst_total, show_saved=True, stream=sys.stderr)}",
              file=sys.stderr)
    return 0 if len(ok) == len(results) and not skipped else 1


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    lower_priority(args.nice)
    sources = collect_inputs(args.inputs, args.recursive, args.outdir)
    if not sources:
        print("対象の動画が見つかりませんでした", file=sys.stderr)
        return 1

    # 対話より先に解析する。何本が複数音声で、どれに字幕があるのかを知ってからでないと
    # 「どの音声を残すか」「字幕が落ちるがよいか」を聞けない。
    announce_inputs(args, len(sources))
    scan, probe_failures = scan_inputs(sources)
    if not scan:
        print("解析できる動画がありませんでした", file=sys.stderr)
        return 1

    cfg = resolve_options(args, scan)
    announce_settings(cfg)
    jobs, skipped = plan_jobs(scan, cfg)
    skipped += probe_failures
    if not jobs:
        print("処理対象がありません", file=sys.stderr)
        return 1 if skipped else 0

    layout = ResultLayout.for_jobs(jobs)
    results = run_jobs(jobs, cfg, layout)
    if cfg.dry_run:
        return 1 if skipped else 0
    return report(results, skipped, any(len(job.plan.tracks) > 1 for job in jobs), layout)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
