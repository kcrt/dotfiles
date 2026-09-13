# -*- coding: utf-8 -*-
"""Move files to the macOS Trash.

The Trash rather than unlink, because what gets removed is the original. Going
through Finder (osascript) would also enable "Put Back", but Finder is
unreachable over ssh and from launchd, where it always fails. Being able to pull
the file back out of the Trash is enough, so an mv-equivalent will do.

Use the standard library only (see termtext for why).
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path


def trash_directory(path: Path) -> Path:
    """The Trash on the same volume as `path`, created if missing.

    Moving across volumes copies the bytes, which is not instant for large files.
    On the boot volume that is ~/.Trash; on an external one, that volume's
    .Trashes/<uid>.
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
    """Move a file to the Trash. Raises OSError if it cannot be moved."""
    trash = trash_directory(path)
    destination = trash / path.name
    if destination.exists():
        # Same name is already in the Trash. Append the timestamp so the earlier
        # file is not overwritten.
        destination = trash / f"{path.stem} {datetime.now():%Y-%m-%d-%H-%M-%S}{path.suffix}"
    path.rename(destination)
