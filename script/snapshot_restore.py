#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""APFS ローカルスナップショットから、消したファイル・古い版を取り戻す。

macOS は Time Machine の有無に関わらず約24〜48時間分のローカルスナップショットを
起動ディスクに持っている。sudo なしで読み取り専用マウントできるので、
「さっき消した」「上書きしてしまった」を NAS を待たずに復旧できる。

    snapshot_restore.py snapshots            # 世代の一覧
    snapshot_restore.py list <path>          # 各世代でそのパスがどうなっているか
    snapshot_restore.py restore <path>       # 世代を選んで復元

⚠️ ローカルスナップショットは短期間で消える。それより古いものは QNAP の
   Time Machine（`tmutil listbackups`）を見ること。このスクリプトは扱わない。
"""

from __future__ import annotations

import argparse
import contextlib
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

DATA_VOLUME = Path("/System/Volumes/Data")
SNAPSHOT_PREFIX = "com.apple.TimeMachine."
SNAPSHOT_SUFFIX = ".local"
CHUNK = 1024 * 1024

# 世代グループの ● に振る色（256色）。明背景・暗背景どちらでも読める範囲で選んだ。
GROUP_COLORS = (39, 214, 76, 170, 178, 203, 44, 129)
MISSING_COLOR = 244  # 「なし」の世代はグレー
_USE_COLOR = False


def set_color(mode: str) -> None:
    """`--color auto|always|never` を解釈して色を使うか決める。"""
    global _USE_COLOR
    if mode == "always":
        _USE_COLOR = True
    elif mode == "never":
        _USE_COLOR = False
    else:  # auto: 端末に出すときだけ。NO_COLOR と TERM=dumb は尊重する
        _USE_COLOR = (sys.stdout.isatty()
                      and os.environ.get("NO_COLOR") is None
                      and os.environ.get("TERM") != "dumb")


def marker(row: dict) -> str:
    """行頭の色付き ●。色が使えないときは記号だけで区別できるので何も出さない。"""
    if not _USE_COLOR:
        return ""
    color = (MISSING_COLOR if row["group"] == "-"
             else GROUP_COLORS[row["group_index"] % len(GROUP_COLORS)])
    return f"\033[38;5;{color}m●\033[0m "


# --------------------------------------------------------------------------
# スナップショットの列挙とマウント
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Snapshot:
    """ローカルスナップショット1世代。"""

    name: str
    taken: datetime

    @property
    def stamp(self) -> str:
        """`2026-08-07-111227` 形式（--at で指定するときのキー）。"""
        return self.taken.strftime("%Y-%m-%d-%H%M%S")

    @property
    def age(self) -> str:
        delta = datetime.now() - self.taken
        hours, minutes = divmod(int(delta.total_seconds()) // 60, 60)
        return f"{hours}時間{minutes:02d}分前" if hours else f"{minutes}分前"


def list_snapshots() -> list[Snapshot]:
    """ローカルスナップショットを新しい順に返す。"""
    result = subprocess.run(
        ["tmutil", "listlocalsnapshots", "/"],
        capture_output=True, text=True, check=True,
    )
    snapshots: list[Snapshot] = []
    for line in result.stdout.splitlines():
        name = line.strip()
        if not name.startswith(SNAPSHOT_PREFIX):
            continue
        stamp = name[len(SNAPSHOT_PREFIX):].removesuffix(SNAPSHOT_SUFFIX)
        try:
            taken = datetime.strptime(stamp, "%Y-%m-%d-%H%M%S")
        except ValueError:
            continue  # 見慣れない名前の世代は触らない
        snapshots.append(Snapshot(name=name, taken=taken))
    return sorted(snapshots, key=lambda s: s.taken, reverse=True)


@contextlib.contextmanager
def mounted(snapshot: Snapshot) -> Iterator[Path]:
    """スナップショットを読み取り専用でマウントする。抜けるとき必ず umount する。"""
    mountpoint = Path(tempfile.mkdtemp(prefix="snapshot_restore."))
    try:
        result = subprocess.run(
            ["mount_apfs", "-o", "ro", "-s", snapshot.name,
             str(DATA_VOLUME), str(mountpoint)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"{snapshot.stamp} のマウントに失敗しました: "
                f"{(result.stderr or result.stdout).strip()}"
            )
        try:
            yield mountpoint
        finally:
            subprocess.run(["umount", str(mountpoint)], capture_output=True)
    finally:
        with contextlib.suppress(OSError):
            mountpoint.rmdir()


# --------------------------------------------------------------------------
# パスの読み替え
# --------------------------------------------------------------------------

def data_relative(path: Path) -> Path:
    """実パスを、データボリューム内の相対パスへ読み替える。

    `/Users/kcrt/x` → `Users/kcrt/x`。存在しない（消した）パスでも使える。
    """
    absolute = Path(os.path.abspath(os.path.expanduser(str(path))))
    if absolute == Path("/"):
        raise ValueError("ルートそのものは対象にできません")

    # 消したパスの場合、実在する一番近い親でボリュームを判定する
    existing = absolute
    while not existing.exists() and existing != existing.parent:
        existing = existing.parent
    if existing.stat().st_dev != DATA_VOLUME.stat().st_dev:
        raise ValueError(
            f"{absolute} は起動ディスクのデータ領域にありません"
            "（外付けや他ボリュームのスナップショットは扱いません）"
        )

    with contextlib.suppress(ValueError):
        return absolute.relative_to(DATA_VOLUME)
    return absolute.relative_to("/")


# --------------------------------------------------------------------------
# 中身の確認
# --------------------------------------------------------------------------

def stamp_of(epoch: float) -> str:
    return datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def tree_digest(root: Path) -> str:
    """ディレクトリ全体を1つのハッシュにまとめる（相対パス＋内容）。"""
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and not p.is_symlink()):
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(sha256(path).encode("ascii"))
    return digest.hexdigest()


def describe(path: Path, with_hash: bool) -> dict:
    """スナップショット内のパスの状態を1件ぶん記述する。

    `latest` は「中身が最後に変わった時刻」。ディレクトリでは配下の全ファイルの
    mtime の最大を取る — **親ディレクトリ自身の mtime は中のファイルが
    書き換わっても動かない**ので、それだけで同一判定すると変更を取りこぼす。
    """
    if not path.exists() and not path.is_symlink():
        return {"exists": False}

    own_mtime = path.lstat().st_mtime
    info: dict = {"exists": True, "mtime": stamp_of(own_mtime)}
    if path.is_dir() and not path.is_symlink():
        size = 0
        newest = own_mtime
        count = 0
        for child in path.rglob("*"):
            if not child.is_file():
                continue
            status = child.stat()
            size += status.st_size
            newest = max(newest, status.st_mtime)
            count += 1
        info |= {"kind": "dir", "files": count, "size": size,
                 "latest": stamp_of(newest)}
        if with_hash:
            info["sha256"] = tree_digest(path)
    else:
        info |= {"kind": "file", "files": 1, "size": path.lstat().st_size,
                 "latest": info["mtime"]}
        if with_hash and path.is_file():
            info["sha256"] = sha256(path)
    return info


def volume(row: dict) -> str:
    """一覧に出す「量」の欄。ファイルならサイズだけ、ディレクトリなら件数も添える。"""
    if row["kind"] == "dir":
        return f"{row['files']:>4}ファイル  {human(row['size']):>9}"
    return f"{'':>4}          {human(row['size']):>9}"


def human(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024:
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{value:.1f}PB"


def group_name(index: int) -> str:
    """0,1,2… を A,B,…,Z,AA,AB… に変換する。"""
    name = ""
    while True:
        name = chr(ord("A") + index % 26) + name
        index = index // 26 - 1
        if index < 0:
            return name


def label_groups(rows: list[dict], with_hash: bool) -> None:
    """中身が同じ世代に同じ記号を振る（どれを選んでも同じ、を見えるようにする）。

    `--hash` なしのときは ファイル数・合計サイズ・最終更新（`latest`）で判定する。
    同じ秒のうちに同じサイズで書き換えられると取りこぼすので、確実に見たいときは
    `--hash`（SHA256）を使う。
    """
    labels: dict[tuple, int] = {}
    for row in rows:
        if not row["exists"]:
            row |= {"group": "-", "group_index": -1}
            continue
        key = ((row["sha256"],) if with_hash
               else (row["kind"], row["files"], row["size"], row["latest"]))
        index = labels.setdefault(key, len(labels))
        row |= {"group": group_name(index), "group_index": index}


def survey(target: Path, snapshots: list[Snapshot], with_hash: bool) -> list[dict]:
    """全世代について、そのパスの状態を調べる。"""
    relative = data_relative(target)
    rows: list[dict] = []
    for snapshot in snapshots:
        with mounted(snapshot) as mountpoint:
            row = {"snapshot": snapshot.stamp, "age": snapshot.age}
            row |= describe(mountpoint / relative, with_hash)
            rows.append(row)
    label_groups(rows, with_hash)
    return rows


# --------------------------------------------------------------------------
# 復元
# --------------------------------------------------------------------------

def verify(source: Path, restored: Path) -> tuple[int, list[str]]:
    """復元先がスナップショットの中身と SHA256 で一致するか確かめる。"""
    mismatches: list[str] = []
    checked = 0

    if source.is_file() and not source.is_symlink():
        pairs = [(source, restored, Path(source.name))]
    else:
        pairs = [(p, restored / p.relative_to(source), p.relative_to(source))
                 for p in sorted(source.rglob("*"))
                 if p.is_file() and not p.is_symlink()]

    for original, copy, label in pairs:
        if not copy.is_file() or sha256(original) != sha256(copy):
            mismatches.append(str(label))
        else:
            checked += 1
    return checked, mismatches


def choose_snapshot(rows: list[dict], snapshots: list[Snapshot]) -> Snapshot | None:
    """対話で世代を選ぶ。パスが存在する世代だけを候補にする。"""
    candidates = [(row, s) for row, s in zip(rows, snapshots) if row["exists"]]
    if not candidates:
        return None
    if not sys.stdin.isatty():
        raise SystemExit(
            "対話で選べません。--at <世代> か --latest-existing を指定してください。"
        )

    print("復元できる世代（同じ記号どうしは中身が同じ。どれを選んでも結果は変わらない）:")
    for number, (row, _) in enumerate(candidates, start=1):
        print(f"  {number:2d}) {marker(row)}[{row['group']}] {row['snapshot']}  "
              f"{row['age']:>12}  {volume(row)}  更新={row['latest']}")
    answer = input("番号を選んでください（q で中止）: ").strip()
    if not answer.isdigit() or not 1 <= int(answer) <= len(candidates):
        return None
    return candidates[int(answer) - 1][1]


def restore(args: argparse.Namespace) -> int:
    target = Path(os.path.abspath(os.path.expanduser(args.path)))
    relative = data_relative(target)
    snapshots = list_snapshots()
    if not snapshots:
        print("ローカルスナップショットがありません。", file=sys.stderr)
        return 1

    # --- どの世代から取るか決める ---
    if args.at:
        matched = [s for s in snapshots if args.at in s.stamp]
        if len(matched) != 1:
            print(f"世代 '{args.at}' は {len(matched)} 件に一致しました。"
                  "`snapshots` で確認してください。", file=sys.stderr)
            return 1
        snapshot = matched[0]
    else:
        rows = survey(target, snapshots, with_hash=not args.no_hash)
        if args.latest_existing:
            found = next((s for row, s in zip(rows, snapshots) if row["exists"]), None)
            if found is None:
                print(f"{target} はどの世代にもありませんでした。", file=sys.stderr)
                return 1
            snapshot = found
        else:
            chosen = choose_snapshot(rows, snapshots)
            if chosen is None:
                print("中止しました。")
                return 1
            snapshot = chosen

    # --- 復元先を決める（既定では原本を上書きしない） ---
    if args.in_place:
        destination = target
        if destination.exists():
            print(f"{destination} が既にあります。--in-place では上書きしません。",
                  file=sys.stderr)
            return 1
    elif args.to:
        destination = Path(os.path.abspath(os.path.expanduser(args.to))) / target.name
    else:
        destination = target.with_name(f"{target.name}.restored-{snapshot.stamp}")
    if destination.exists():
        print(f"復元先 {destination} が既にあります。消すか --to で別の場所を指定してください。",
              file=sys.stderr)
        return 1

    # --- コピー → 照合 ---
    with mounted(snapshot) as mountpoint:
        source = mountpoint / relative
        if not source.exists() and not source.is_symlink():
            print(f"{snapshot.stamp} に {target} はありません。", file=sys.stderr)
            return 1

        destination.parent.mkdir(parents=True, exist_ok=True)
        print(f"{snapshot.stamp}（{snapshot.age}）から復元します")
        print(f"  → {destination}")
        if source.is_dir() and not source.is_symlink():
            shutil.copytree(source, destination, symlinks=True)
        else:
            shutil.copy2(source, destination, follow_symlinks=False)

        if args.no_verify:
            print("SHA256 照合は省きました（--no-verify）。")
            return 0

        checked, mismatches = verify(source, destination)

    if mismatches:
        print(f"⚠️ SHA256 が一致しないファイルが {len(mismatches)} 件あります:",
              file=sys.stderr)
        for label in mismatches[:10]:
            print(f"    {label}", file=sys.stderr)
        print("復元先はそのまま残しました。中身を確認してください。", file=sys.stderr)
        return 1

    print(f"SHA256 一致 {checked} 件。復元しました。")
    return 0


# --------------------------------------------------------------------------
# サブコマンド
# --------------------------------------------------------------------------

LIVE_WORDS = {"now", "live", "current"}  # "." はカレントディレクトリと紛らわしいので入れない
REF_PATTERN = re.compile(r"[A-Z]{1,2}$|[0-9][0-9-]*$")
TEXT_LIMIT = 5 * 1024 * 1024  # これより大きいファイルは中身を読まず「違う」とだけ言う


def resolve_ref(ref: str, target: Path, snapshots: list[Snapshot]) -> Snapshot | None:
    """`2026-08-07-091052` / 部分一致 / グループ記号 `A` / `now` を世代に読み替える。

    None を返したら「今の（生きている）ファイル」を指す。
    """
    if ref.lower() in LIVE_WORDS:
        return None

    matched = [s for s in snapshots if ref in s.stamp]
    if len(matched) == 1:
        return matched[0]
    if len(matched) > 1:
        raise ValueError(f"世代 '{ref}' は {len(matched)} 件に一致します。もう少し絞ってください")

    if ref.isalpha() and ref.isupper():  # list で見た [A] [B] をそのまま使える
        rows = survey(target, snapshots, with_hash=True)
        members = [s for row, s in zip(rows, snapshots) if row["group"] == ref]
        if members:
            return members[0]  # 同じ記号なら中身は同じなので、いちばん新しい世代を代表にする
        raise ValueError(f"記号 '{ref}' の世代がありません。`list` で確認してください")

    raise ValueError(f"'{ref}' を世代として解釈できません（例: 2026-08-07-091052 / A / now）")


def state_of(snapshot: Snapshot | None, relative: Path) -> tuple[dict[str, str], bytes | None]:
    """世代（None なら現物）における、パス配下の「相対パス→SHA256」と、
    単一ファイルならその中身を返す。"""

    def collect(root: Path) -> tuple[dict[str, str], bytes | None]:
        if not root.exists():
            return ({}, None)
        if root.is_file():
            content = root.read_bytes() if root.stat().st_size <= TEXT_LIMIT else None
            return ({root.name: sha256(root)}, content)
        return ({str(p.relative_to(root)): sha256(p)
                 for p in root.rglob("*") if p.is_file()}, None)

    if snapshot is None:
        return collect(Path("/") / relative)
    with mounted(snapshot) as mountpoint:
        return collect(mountpoint / relative)


def ref_label(snapshot: Snapshot | None) -> str:
    return f"{snapshot.stamp}（{snapshot.age}）" if snapshot else "現在のファイル"


def paint(text: str, code: int) -> str:
    return f"\033[38;5;{code}m{text}\033[0m" if _USE_COLOR else text


def unified(before: bytes, after: bytes, left: str, right: str) -> list[str] | None:
    """テキストとして読めるなら unified diff を返す。バイナリなら None。"""
    try:
        old = before.decode("utf-8").splitlines(keepends=True)
        new = after.decode("utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        return None
    return list(difflib.unified_diff(old, new, fromfile=left, tofile=right))


def looks_like_ref(token: str) -> bool:
    """`A` `2026-08-07-091052` `now` のような、世代の指定に見えるか。"""
    return token.lower() in LIVE_WORDS or bool(REF_PATTERN.fullmatch(token))


def split_diff_args(tokens: list[str]) -> tuple[str, str, str | None]:
    """`diff [path] a [b]` を読み分ける。

    path は省略できるので、`diff A B` の `A` を path と誤解しないよう、
    世代に見えるトークンで、かつ同名のファイルが無いときだけ世代として扱う。
    """
    if len(tokens) > 3:
        raise ValueError("引数が多すぎます。`diff [パス] <比較元> [比較先]` の形で指定してください")
    if len(tokens) == 3:
        return tokens[0], tokens[1], tokens[2]
    if len(tokens) == 1:
        return ".", tokens[0], None

    first, second = tokens
    if looks_like_ref(first) and not Path(os.path.expanduser(first)).exists():
        return ".", first, second
    return first, second, None


def cmd_diff(args: argparse.Namespace) -> int:
    path, ref_a, ref_b = split_diff_args(args.tokens)
    target = Path(os.path.abspath(os.path.expanduser(path)))
    relative = data_relative(target)
    snapshots = list_snapshots()
    if not snapshots:
        print("ローカルスナップショットがありません。", file=sys.stderr)
        return 1

    left_ref = resolve_ref(ref_a, target, snapshots)
    right_ref = resolve_ref(ref_b, target, snapshots) if ref_b else None

    left, left_bytes = state_of(left_ref, relative)
    right, right_bytes = state_of(right_ref, relative)
    if not left and not right:
        print(f"{target} はどちらにも存在しません。", file=sys.stderr)
        return 1

    print(f"{target}\n  {ref_label(left_ref)}  →  {ref_label(right_ref)}")

    added = sorted(set(right) - set(left))
    removed = sorted(set(left) - set(right))
    changed = sorted(name for name in set(left) & set(right) if left[name] != right[name])
    if not (added or removed or changed):
        print("  差分なし")
        return 0

    for name in changed:
        print(paint(f"  ~ {name}", 214))
    for name in added:
        print(paint(f"  + {name}", 76))
    for name in removed:
        print(paint(f"  - {name}", 203))
    print(f"  差分 {len(changed) + len(added) + len(removed)} 件"
          f"（変更 {len(changed)} / 追加 {len(added)} / 削除 {len(removed)}）")

    # 単一ファイルを比べたときは、そのまま中身の差分まで出す
    if changed and left_bytes is not None and right_bytes is not None:
        lines = unified(left_bytes, right_bytes,
                        ref_label(left_ref), ref_label(right_ref))
        if lines is None:
            print("  （バイナリのため中身の差分は出しません）")
        else:
            print()
            for line in lines:
                color = 76 if line.startswith("+") else 203 if line.startswith("-") else None
                text = line.rstrip("\n")
                print(paint(text, color) if color else text)
    return 0


def cmd_snapshots(args: argparse.Namespace) -> int:
    snapshots = list_snapshots()
    if args.json:
        print(json.dumps([{"snapshot": s.stamp, "name": s.name, "age": s.age}
                          for s in snapshots], ensure_ascii=False, indent=2))
        return 0
    if not snapshots:
        print("ローカルスナップショットがありません。")
        return 1
    print(f"ローカルスナップショット {len(snapshots)} 世代:")
    for snapshot in snapshots:
        print(f"  {snapshot.stamp}  {snapshot.age:>12}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    target = Path(os.path.abspath(os.path.expanduser(args.path)))
    snapshots = list_snapshots()
    if not snapshots:
        print("ローカルスナップショットがありません。", file=sys.stderr)
        return 1

    with_hash = not args.no_hash
    rows = survey(target, snapshots, with_hash=with_hash)
    if args.json:
        print(json.dumps({"path": str(target), "snapshots": rows},
                         ensure_ascii=False, indent=2))
        return 0

    print(f"{target} の各世代での状態:")
    for row in rows:
        if not row["exists"]:
            print(f"  {marker(row)}[{row['group']}] {row['snapshot']}  "
                  f"{row['age']:>12}  （なし）")
            continue
        line = (f"  {marker(row)}[{row['group']}] {row['snapshot']}  {row['age']:>12}  "
                f"{volume(row)}  更新={row['latest']}")
        if with_hash:
            line += f"  {row['sha256'][:12]}"
        print(line)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="APFS ローカルスナップショットから消したファイル・古い版を取り戻す",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="例:\n"
               "  snapshot_restore.py list ~/Documents/大事なフォルダ\n"
               "  snapshot_restore.py restore ~/Documents/大事なフォルダ --latest-existing\n"
               "  snapshot_restore.py restore ~/x.txt --at 2026-08-07-111227 --to ~/Desktop\n",
    )
    # --color はサブコマンドの前後どちらに書いても効くよう、両方に生やす。
    # サブコマンド側は dest を分けておかないと、既定値が前置きの指定を上書きしてしまう。
    def add_color_option(target: argparse.ArgumentParser, dest: str, default: str | None):
        target.add_argument("--color", dest=dest, default=default,
                            choices=("auto", "always", "never"),
                            help="世代グループの ● に色を付ける（既定: auto＝端末のときだけ）")

    add_color_option(parser, "color", "auto")
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshots_parser = subparsers.add_parser("snapshots", help="世代の一覧を表示する")
    snapshots_parser.add_argument("--json", action="store_true", help="JSON で出力する")
    snapshots_parser.set_defaults(func=cmd_snapshots)

    list_parser = subparsers.add_parser(
        "list", aliases=["ls"], help="各世代でそのパスがどうなっているかを調べる")
    list_parser.add_argument("path", nargs="?", default=".",
                             help="調べるファイル／ディレクトリ（省略時はカレント）")
    list_parser.add_argument("--no-hash", action="store_true",
                             help="SHA256 を取らず、ファイル数・合計サイズ・最終更新だけで"
                                  "速く判定する（同秒・同サイズの書き換えを取りこぼす）")
    list_parser.add_argument("--json", action="store_true", help="JSON で出力する")
    list_parser.set_defaults(func=cmd_list)

    diff_parser = subparsers.add_parser(
        "diff", help="2つの世代（または現在）を突き合わせて、変わったファイルを出す")
    diff_parser.add_argument(
        "tokens", nargs="+", metavar="[パス] 比較元 [比較先]",
        help="世代は 2026-08-07-091052（部分一致可）・list で見た記号 A・now のいずれか。"
             "パスを省略するとカレント、比較先を省略すると現在のファイルと比べる")
    diff_parser.set_defaults(func=cmd_diff)

    restore_parser = subparsers.add_parser("restore", help="世代を選んで復元する")
    restore_parser.add_argument("path", help="復元したいファイル／ディレクトリの元のパス")
    restore_parser.add_argument("--at", metavar="世代",
                                help="世代を直接指定する（例: 2026-08-07-111227）")
    restore_parser.add_argument("--latest-existing", action="store_true",
                                help="そのパスが残っている最新の世代を自動で選ぶ")
    restore_parser.add_argument("--to", metavar="DIR", help="復元先のディレクトリ")
    restore_parser.add_argument("--in-place", action="store_true",
                                help="元の場所へ戻す（既存があれば中止する）")
    restore_parser.add_argument("--no-verify", action="store_true",
                                help="復元後の SHA256 照合を省く（既定は照合する）")
    restore_parser.add_argument("--no-hash", action="store_true",
                                help="世代の同一判定に SHA256 を使わず速く済ませる")
    restore_parser.set_defaults(func=restore)

    for subparser in (snapshots_parser, list_parser, diff_parser, restore_parser):
        add_color_option(subparser, "color_after", None)

    if len(sys.argv) == 1:  # 引数なしは使い方を出す（そっけない usage で終わらせない）
        parser.print_help()
        return 1

    args = parser.parse_args()
    set_color(args.color_after or args.color)
    if sys.platform != "darwin":
        print("macOS 専用です。", file=sys.stderr)
        return 1
    try:
        return args.func(args)
    except (ValueError, RuntimeError) as error:
        print(f"エラー: {error}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as error:
        print(f"コマンドが失敗しました: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
