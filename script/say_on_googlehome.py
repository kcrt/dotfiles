#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pychromecast>=14.0.9",
# ]
# ///

"""Find Google Home and speak a message on it.

Can be used as a CLI script or imported as a module.

Example:
    from script.say_on_googlehome import say, list_devices

    # List available devices
    devices = list_devices()

    # Say something on the first device
    say("Hello world!")

    # Say something on a specific device with language
    say("Hallo Welt!", device_name="Living Room", lang="de-DE")
"""

import argparse
import os
import platform
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler

import pychromecast


def parsearg():
    parser = argparse.ArgumentParser(
        description="Say a message on Google Home")
    parser.add_argument("message", help='Message to say', nargs='?')
    parser.add_argument("-n", '--name', help='Name of Google Home device')
    parser.add_argument(
        "-l", '--list', help='List available devices', action='store_true')
    parser.add_argument(
        "-L", '--lang', help='Language for text-to-speech (e.g., "en-US", "ja-JP", "de-DE")')
    parser.add_argument(
        "-t", '--timeout', type=float, default=30.0,
        help='Maximum time to wait for playback to finish (seconds) [default: 30]')
    parser.add_argument(
        "--also-local", action='store_true',
        help='Also play the sound locally')
    return parser.parse_args()


class QuietHTTPRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: ARG002
        # Only log when message.m4a is accessed
        if 'message.m4a' in self.path:
            print(f" [Accessed] message.m4a from {self.address_string()}")


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def start_http_server(directory: str, port: int) -> HTTPServer:
    os.chdir(directory)
    server = HTTPServer(('0.0.0.0', port), QuietHTTPRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _play_local_macos(audio_path: str) -> None:
    """Play audio file locally on macOS using afplay."""
    if not shutil.which('afplay'):
        raise RuntimeError("'afplay' command is not available on this system")
    subprocess.run(['afplay', audio_path], check=True)


def _play_local_linux(audio_path: str) -> None:
    """Play audio file locally on Linux using paplay or aplay."""
    player = None
    for candidate in ('paplay', 'aplay'):
        if shutil.which(candidate):
            player = candidate
            break
    if not player:
        raise RuntimeError("No audio player found. Please install pulseaudio-utils (paplay) or alsa-utils (aplay)")
    subprocess.run([player, audio_path], check=True)


def _convert_to_m4a(input_path: str, output_path: str) -> None:
    """Convert audio file to m4a using ffmpeg."""
    try:
        subprocess.run(
            ['ffmpeg', '-y', '-i', input_path, '-c:a', 'aac', '-b:a', '128k', output_path],
            check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg conversion failed: {e.stderr.decode() if e.stderr else e}") from e
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)


def _synthesize_macos(text: str, output_path: str, lang: str | None) -> str:
    """Synthesize speech using macOS 'say' command. Returns temp audio file path."""
    if not shutil.which('say'):
        raise RuntimeError("'say' command is not available on this system")

    temp_aiff = output_path.replace(".m4a", ".aiff")
    cmd = ['say', '-o', temp_aiff]
    if lang:
        cmd.extend(['-v', lang])
    cmd.append(text)

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"'say' command failed: {e}") from e
    return temp_aiff


def _synthesize_linux(text: str, output_path: str, lang: str | None) -> str:
    """Synthesize speech using Linux 'espeak' command. Returns temp audio file path."""
    if not shutil.which('espeak'):
        raise RuntimeError("'espeak' command is not installed. Please install espeak (e.g., 'sudo apt install espeak' or 'sudo dnf install espeak')")

    temp_wav = output_path.replace(".m4a", ".wav")
    cmd = ['espeak']
    if lang:
        cmd.extend(['-v', lang])
    cmd.extend(['-w', temp_wav, text])

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"'espeak' command failed: {e}") from e
    return temp_wav


def text_to_audio(text: str, output_path: str, lang: str | None = None) -> str:
    """Convert text to m4a audio file. Returns the path to the m4a file."""
    if not shutil.which('ffmpeg'):
        raise RuntimeError("ffmpeg is not installed or not found in PATH")

    system = platform.system()
    if system == "Darwin":
        temp_audio = _synthesize_macos(text, output_path, lang)
    else:
        temp_audio = _synthesize_linux(text, output_path, lang)

    _convert_to_m4a(temp_audio, output_path)
    return output_path


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


class Device:
    """Represents a Chromecast device."""

    def __init__(self, name: str | None, model: str):
        self.name = name
        self.model = model

    def __repr__(self) -> str:
        return f"Device(name={self.name!r}, model={self.model!r})"


def list_devices() -> list[Device]:
    """List available Chromecast devices.

    Returns:
        A list of Device objects representing available Chromecast devices.
    """
    ret = pychromecast.get_chromecasts()
    chromecasts: list[pychromecast.Chromecast] = ret[0]
    return [Device(cc.name, cc.model_name or "Unknown") for cc in chromecasts]


def say(
    message: str,
    device_name: str | None = None,
    lang: str | None = None,
    verbose: bool = True,
    timeout: float = 30.0,
    also_local: bool = False,
) -> None:
    """Speak a message on a Google Home device.

    Args:
        message: The message to speak.
        device_name: Name of the Google Home device. If None, uses the first available device.
        lang: Language for text-to-speech (e.g., "en-US", "ja-JP", "de-DE").
        verbose: Whether to print progress messages.
        timeout: Maximum time to wait for playback to finish, in seconds. Set to 0 to wait indefinitely.
        also_local: Also play the sound locally on the host machine.

    Raises:
        RuntimeError: If no Google Home devices are found, or if audio generation fails.
        TimeoutError: If playback does not finish within the timeout.
    """
    chromecasts: list[pychromecast.Chromecast] = pychromecast.get_chromecasts()[0]

    if len(chromecasts) == 0:
        raise RuntimeError("No Google Home devices found")

    if device_name:
        chromecast = next((cc for cc in chromecasts if cc.name == device_name), None)
        if chromecast is None:
            available = ", ".join(cc.name or "(unnamed)" for cc in chromecasts)
            raise RuntimeError(f"Device '{device_name}' not found. Available devices: {available}")
    else:
        chromecast = chromecasts[0]

    if verbose:
        print(f"Target device: {chromecast.name}")

    # Create temp directory for audio file
    temp_dir = tempfile.mkdtemp()
    audio_file = os.path.join(temp_dir, "message.m4a")

    try:
        # Convert text to audio (m4a format)
        if verbose:
            print(f"Generating audio for: {message}")
            if lang:
                print(f"Language: {lang}")
        text_to_audio(message, audio_file, lang)

        # Play locally if requested
        if also_local:
            if verbose:
                print("Playing locally...")
            system = platform.system()
            if system == "Darwin":
                _play_local_macos(audio_file)
            else:
                _play_local_linux(audio_file)

        # Start HTTP server to serve the audio file
        port = get_free_port()
        server = start_http_server(temp_dir, port)
        print(f"Started HTTP server on port {port}")

        local_ip = get_local_ip()
        audio_url = f"http://{local_ip}:{port}/message.m4a"

        # Play on chromecast
        chromecast.wait()

        # Stop any current playback and clear queue to ensure our message plays
        print("Stopping current playback and clearing queue...")
        try:
            chromecast.quit_app()
            time.sleep(2)  # Give it a moment to stop
        except Exception:
            # No active session, nothing to stop
            print("No active app to close")

        chromecast.wait()
        mc = chromecast.media_controller

        print(f"Request for play: {audio_url}")
        mc.play_media(audio_url, "audio/mp4")
        mc.block_until_active()

        # Wait for a second
        time.sleep(1)

        # Ensure playback actually starts (media might load but stay paused)
        if mc.status.player_state == "PAUSED":
            print(f"Playback is paused, resuming...")
            mc.play()
            time.sleep(1)

        # Check current status/queue before playing
        print(f"Current state: {mc.status.player_state}")
        if mc.status.player_state in ("PLAYING", "PAUSED", "BUFFERING"):
            print(f"Current content: {mc.status.title or 'Unknown'}")
            if mc.status.artist:
                print(f"Artist: {mc.status.artist}")
        elif mc.status.player_state == "UNKNOWN":
            print("No active session detected")

        # Wait for playback to finish
        start_time = time.time()
        while True:
            state = mc.status.player_state
            print(state)
            if state in ("IDLE", "PAUSED"):
                print("Playback finished")
                break
            elif timeout > 0 and time.time() - start_time > timeout:
                raise TimeoutError(f"Playback did not finish within {timeout} seconds")
            time.sleep(0.5)

        if verbose:
            print("Done!")
        server.shutdown()

    finally:
        # Cleanup temp directory
        shutil.rmtree(temp_dir)


def main():
    args = parsearg()

    if args.list:
        devices = list_devices()
        for device in devices:
            print(f"{device.name} ({device.model})")
        return

    if args.message is None:
        print("No message to say")
        return

    try:
        say(args.message, device_name=args.name, lang=args.lang, timeout=args.timeout, also_local=args.also_local)
    except RuntimeError as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
