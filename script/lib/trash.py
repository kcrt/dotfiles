# -*- coding: utf-8 -*-
"""macOSのゴミ箱へ移す。

unlinkではなくゴミ箱にするのは、消すのが原本だから。Finder経由（osascript）なら
「戻す」も効くが、ssh・launchdではFinderに繋がらず必ず失敗する。ゴミ箱から
取り出せれば足りるので、mv相当で済ませる。

標準ライブラリだけで書くこと（理由は termtext を参照）。
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path


def trash_directory(path: Path) -> Path:
    """path と同じボリュームにあるゴミ箱。無ければ作る。

    ボリュームを跨ぐ移動は実体のコピーになり、大きなファイルでは一瞬で終わらない。
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
    """ファイルをゴミ箱へ移す。移せなければ OSError。"""
    trash = trash_directory(path)
    destination = trash / path.name
    if destination.exists():
        # 同名が既にゴミ箱にある。日時を足して、先に捨てた方を上書きしない
        destination = trash / f"{path.stem} {datetime.now():%Y-%m-%d-%H-%M-%S}{path.suffix}"
    path.rename(destination)
