#!/usr/bin/env -S uv run

# Split mp4 audio file into multiple files by chapters

import json
import os
import sys
import subprocess
import re
import argparse
from typing import Any
from dataclasses import dataclass

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


def generate_filename(file: str, chapter: Chapter, force_m4a: bool = False) -> str:
    filename, ext = os.path.splitext(file)
    if force_m4a:
        ext = '.m4a'
    return f'{filename}_{chapter.id+1:02d}{ext}'


def humanize_time(seconds: float) -> str:
    # Convert seconds to hours, minutes and seconds
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f'{int(h):02}:{int(m):02}:{int(s):02}'


def split_chapter(file: str, chapter: Chapter, probe_result: FFProbeResult, force_m4a: bool = False, clear_metadata: bool = False):
    filename = generate_filename(file, chapter, force_m4a)
    title = chapter.tags.get('title', '')
    chapter_id = chapter.id
    disc = probe_result.format.tags.get('disc', '')
    album_title = probe_result.format.tags.get('album', '')
    cmd = f'ffmpeg -i "{file}" -ss {chapter.start_time} -to {chapter.end_time} -c copy'
    if force_m4a:
        cmd = cmd + ' -vn'
    if clear_metadata:
        # clear existing metadata
        cmd = cmd + ' -map_metadata -1'
    cmd = cmd + f' -map_chapters -1 -metadata track={chapter_id+1} -metadata title="{title}" -metadata album="{album_title}" -metadata disc="{disc}" -metadata genre="music"'
    cmd = cmd + f' "{filename}"'
    print(f'Splitting chapter: {title} -> {filename}')
    print(cmd)
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

    if not probe_result or not probe_result.chapters:
        print('No chapters found.')
        sys.exit(1)

    # Show chapters
    print(f'Album title: {probe_result.format.tags.get("album", "")}')
    for i, chapter in enumerate(probe_result.chapters):
        print(f'{i+1:02d}. {humanize_time(chapter.start_time)} - {humanize_time(chapter.end_time)}: {chapter.tags.get("title", "")}')

    # Ask for confirmation
    if not args.yes:
        confirm = input('Do you want to split the file? (y/n): ')    
        if confirm.lower() != 'y':
            sys.exit(0)

    # Split chapters
    for chapter in probe_result.chapters:
        split_chapter(file, chapter, probe_result, args.m4a, args.clear_metadata)
    
    print('All chapters have been split successfully.')



if __name__ == '__main__':
    main()