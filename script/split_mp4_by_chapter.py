#!/usr/bin/env -S uv run

# Split mp4 audio file into multiple files by chapters

import os
import sys
import subprocess
import argparse

from lib.ffprobe import Chapter, ProbeError, ProbeResult, probe_chapters
from lib.humanize import clock
from lib.prompt import confirm


def generate_filename(file: str, chapter: Chapter, force_m4a: bool = False) -> str:
    filename, ext = os.path.splitext(file)
    if force_m4a:
        ext = '.m4a'
    return f'{filename}_{chapter.id+1:02d}{ext}'


def split_chapter(file: str, chapter: Chapter, probe_result: ProbeResult, force_m4a: bool = False, clear_metadata: bool = False):
    filename = generate_filename(file, chapter, force_m4a)
    title = chapter.title
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
    try:
        probe_result = probe_chapters(file)
    except ProbeError as error:
        print(f'Cannot read {file}: {error}')
        sys.exit(1)

    if not probe_result.chapters:
        print('No chapters found.')
        sys.exit(1)

    # Show chapters
    print(f'Album title: {probe_result.format.tags.get("album", "")}')
    for i, chapter in enumerate(probe_result.chapters):
        print(f'{i+1:02d}. {clock(chapter.start_time, always_hours=True)} - '
              f'{clock(chapter.end_time, always_hours=True)}: {chapter.title}')

    # Ask for confirmation
    if not args.yes and not confirm('Do you want to split the file?'):
        sys.exit(0)

    # Split chapters
    for chapter in probe_result.chapters:
        split_chapter(file, chapter, probe_result, args.m4a, args.clear_metadata)
    
    print('All chapters have been split successfully.')



if __name__ == '__main__':
    main()