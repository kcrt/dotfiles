#!/usr/bin/env -S uv run

# Keep only audio stream (and tag) of mp4 audio file

import os
import sys
import subprocess
import argparse

from lib.ffprobe import ProbeError, ProbeResult, probe_chapters


def keep_audio_stream(file: str, probe_result: ProbeResult):
    newfilename = file.replace('.m4a', '_audio.m4a')
    artist = probe_result.format.tags.get('artist', '')
    title = probe_result.format.tags.get('title', '')
    disc = probe_result.format.tags.get('disc', '')
    track_id = probe_result.format.tags.get('track', '')
    album_title = probe_result.format.tags.get('album', '')

    cmd = f'ffmpeg -i "{file}" -vn -map 0:a -c:a copy -map_metadata -1 -metadata artist="{artist}" -metadata title="{title}" -metadata album="{album_title}" -metadata disc="{disc}" -metadata track="{track_id}" "{newfilename}"'
    subprocess.run(cmd, shell=True)


def main():
    parser = argparse.ArgumentParser(description='Keep only the audio stream of an mp4 audio file, carrying the tags over')
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
    keep_audio_stream(file, probe_result)
    
    print('Done.')



if __name__ == '__main__':
    main()