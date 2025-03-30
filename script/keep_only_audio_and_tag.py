#!/usr/bin/env python3

# Keep only audio stream (and tag) of mp4 audio file

import json
import os
import sys
import subprocess
import re
import argparse
from typing import Any

from attr import dataclass
from nbformat import from_dict

@dataclass
class Format:
    filename: str
    duration: float
    bit_rate: int
    tags: dict[str, str]

    @staticmethod
    def from_dict(d: dict[str, Any]) -> 'Format':
        return Format(
            filename=d['filename'],
            duration=float(d['duration']),
            bit_rate=int(d['bit_rate']),
            tags=d['tags']
        )

@dataclass
class Chapter:
    id: int
    time_base: str
    start: int
    start_time: float
    end: int
    end_time: float
    tags: dict[str, str]
    
    @staticmethod
    def from_dict(d: dict[str, Any]) -> 'Chapter':
        return Chapter(
            id=d['id'],
            time_base=d['time_base'],
            start=d['start'],
            start_time=float(d['start_time']),
            end=d['end'],
            end_time=float(d['end_time']),
            tags=d['tags']
        )

@dataclass
class FFProbeResult:
    chapters: list[Chapter]
    format: Format

    @staticmethod
    def from_dict(d: dict[str, Any]) -> 'FFProbeResult':
        return FFProbeResult(
            chapters=[Chapter.from_dict(chapter) for chapter in d['chapters']],
            format=Format.from_dict(d['format'])
        )


def ffprobe(file: str) -> FFProbeResult | None:
    cmd = 'ffprobe -v error -of json -show_chapters -show_format "{}"'.format(file)
    ret_jsonstr = subprocess.check_output(cmd, shell=True).decode('utf-8')
    ret_json = json.loads(ret_jsonstr)
    return FFProbeResult.from_dict(ret_json) if ret_json else None


def keep_audio_stream(file: str, probe_result: FFProbeResult):
    newfilename = file.replace('.m4a', '_audio.m4a')
    artist = probe_result.format.tags.get('artist', '')
    title = probe_result.format.tags.get('title', '')
    disc = probe_result.format.tags.get('disc', '')
    track_id = probe_result.format.tags.get('track', '')
    album_title = probe_result.format.tags.get('album', '')

    cmd = f'ffmpeg -i "{file}" -vn -map 0:a -c:a copy -map_metadata -1 -metadata artist="{artist}" -metadata title="{title}" -metadata album="{album_title}" -metadata disc="{disc}" -metadata track="{track_id}" "{newfilename}"'
    subprocess.run(cmd, shell=True)


def main():
    parser = argparse.ArgumentParser(description='Split mp4 audio file into multiple files by chapters')
    parser.add_argument('file', help='mp4 audio file')
    parser.add_argument('--yes', '-y', action='store_true', help='Do not ask for confirmation')
    parser.add_argument('--m4a', '-m', action='store_true', help='Force output to m4a format')
    parser.add_argument('--clear-metadata', '-c', action='store_true', help='Clear metadata from output files (only set track, disk, title, album, and genre=music)')
    args = parser.parse_args()

    file: str = args.file
    if not os.path.exists(file):
        print(f'File not found: {file}')
        sys.exit(1)
    probe_result = ffprobe(file)
    if not probe_result:
        print(f'Failed to probe file: {file}')
        sys.exit(1)
    keep_audio_stream(file, probe_result)
    
    print('All chapters have been split successfully.')



if __name__ == '__main__':
    main()