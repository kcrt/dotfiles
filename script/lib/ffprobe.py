# -*- coding: utf-8 -*-
"""Read a media file's chapters and container metadata with ffprobe.

Scripts that split or retag audio need the same two things: the chapter list and
the container's format block (duration, bitrate, tags). Both come out of one
ffprobe call, which is what probe_chapters() wraps.

The raw JSON is available through probe_json() for the other sections
(-show_streams and friends), so nothing has to assemble an ffprobe command line
by hand. That matters beyond tidiness: building one by interpolating a filename
into a shell string breaks on names containing a quote, a space or a $, and the
argument list used here cannot.

This does not cover ffmpeg-convert.py, which needs resolution, frame rate and the
per-stream audio layout, and models them in its own MediaInfo.

Use the standard library only (see termtext for why).
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ffprobe is quiet on success and prints only real errors, so stderr is worth
# quoting back verbatim when it fails.
FFPROBE_BASE = ("ffprobe", "-v", "error", "-of", "json")


class ProbeError(RuntimeError):
    """ffprobe could not read the file (missing, not media, or ffprobe absent)."""


@dataclass(frozen=True)
class Format:
    """The container as a whole."""

    filename: str
    duration: float
    bit_rate: int
    tags: dict[str, str]

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Format":
        # duration and bit_rate are missing for some containers (a raw stream, or
        # a file still being written), so neither is required to build the object.
        return Format(
            filename=d.get("filename", ""),
            duration=float(d.get("duration", 0.0)),
            bit_rate=int(d.get("bit_rate", 0)),
            tags=d.get("tags", {}),
        )


@dataclass(frozen=True)
class Chapter:
    """One chapter, with its bounds already converted to seconds."""

    id: int
    time_base: str
    start: int
    start_time: float
    end: int
    end_time: float
    tags: dict[str, str]

    @property
    def title(self) -> str:
        """The chapter title, or "" for a file whose chapters are unnamed."""
        return self.tags.get("title", "")

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Chapter":
        return Chapter(
            id=d["id"],
            time_base=d.get("time_base", ""),
            start=int(d.get("start", 0)),
            start_time=float(d.get("start_time", 0.0)),
            end=int(d.get("end", 0)),
            end_time=float(d.get("end_time", 0.0)),
            tags=d.get("tags", {}),
        )


@dataclass(frozen=True)
class ProbeResult:
    """What one `-show_chapters -show_format` run returns."""

    chapters: list[Chapter]
    format: Format

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "ProbeResult":
        return ProbeResult(
            chapters=[Chapter.from_dict(chapter) for chapter in d.get("chapters", [])],
            format=Format.from_dict(d.get("format", {})),
        )


def probe_json(path: Path | str, *sections: str) -> dict[str, Any]:
    """Run ffprobe over one file and return the parsed JSON.

    `sections` are the -show_* options wanted, e.g. "-show_streams".
    Raises ProbeError with ffprobe's own last line of stderr, which says more than
    a return code ("Invalid data found when processing input", "No such file").
    """
    command = [*FFPROBE_BASE, *sections, str(path)]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise ProbeError("ffprobe not found (brew install ffmpeg)") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip().splitlines()
        raise ProbeError(detail[-1] if detail else f"ffprobe failed: {path}")
    return json.loads(completed.stdout)


def probe_chapters(path: Path | str) -> ProbeResult:
    """Read the chapter list and the format block of one file."""
    return ProbeResult.from_dict(probe_json(path, "-show_chapters", "-show_format"))
