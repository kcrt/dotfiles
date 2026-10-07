# -*- coding: utf-8 -*-
"""Report a job's progress to the terminal multiplexer's status bar.

The status bar (zjstatus in zellij) polls `progress_info.sh`, which shows both
the file transfers it sees on its own and whatever a job reported by hand under
a title. This wraps the reporting half, so that a script does not have to spell
out the command line:

    with StatusProgress("ff🔄", total=len(jobs)) as status:
        for done, job in enumerate(jobs, start=1):
            run(job)
            status.update(done, text=job.name)

progress_info.sh is the single owner of the storage format; this only calls it.
Reporting is best effort: a status bar that cannot be updated (the script is
missing, the state directory is read-only) must never fail the job itself, so
every error is swallowed.

Use the standard library only (see termtext for why).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Self

# The script that stores and renders the entries, next to this package.
PROGRESS_INFO = Path(__file__).resolve().parent.parent / "progress_info.sh"


def report_progress(title: str, num: int | None = None, total: int | None = None,
                    text: str | None = None, pid: int | None = None) -> None:
    """Create or update the entry for `title`. Fields left as None keep their value."""
    args = ["--title", title]
    if num is not None:
        args += ["--num", str(num)]
    if total is not None:
        args += ["--of", str(total)]
    if text is not None:
        args += ["--set", text]
    if pid is not None:
        args += ["--pid", str(pid)]
    _run(args)


def finish_progress(title: str) -> None:
    """Mark the entry finished; the status bar shows it briefly, then drops it."""
    _run(["--title", title, "--done"])


def _run(args: list[str]) -> None:
    try:
        subprocess.run([str(PROGRESS_INFO), *args], check=False, timeout=5,
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        pass


class StatusProgress:
    """An entry that lives for the duration of a `with` block.

    It is registered with this process's pid, so a run killed outright (SIGKILL,
    a closed terminal) is shown as failed at the next poll, briefly, instead of
    lingering as if still running. Leaving the block by any route, an exception
    or Ctrl-C included, marks it finished.
    """

    def __init__(self, title: str, total: int | None = None, text: str | None = None,
                 enabled: bool = True) -> None:
        self.title = title
        self.total = total
        self.text = text
        self.enabled = enabled

    def __enter__(self) -> Self:
        if self.enabled:
            report_progress(self.title, 0 if self.total is not None else None,
                            self.total, self.text, pid=os.getpid())
        return self

    def update(self, num: int | None = None, text: str | None = None) -> None:
        if self.enabled:
            report_progress(self.title, num, None, text)

    def __exit__(self, *exc: object) -> None:
        if self.enabled:
            finish_progress(self.title)
