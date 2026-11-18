#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "numpy",
#     "pyaudio",
# ]
# ///

# This script is a GUI application that monitors audio input,
# displays a history of volume levels, and allows playback of
# recorded segments. It is designed to detect snoring (ibiki)
# and can optionally play a sound if a volume threshold is exceeded.

import tkinter as tk
from tkinter import ttk
import pyaudio
import numpy as np
import threading
import time
from collections import deque
import queue
import shutil
import subprocess
import sys
from pathlib import Path

# --- Constants ---
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
BAR_SECONDS = 0.25 # How long each bar of the graph represents
CHUNKS_PER_BAR = round(RATE * BAR_SECONDS / CHUNK) # 11 chunks (~0.26 s)
# Wakeup detection judges ~1 s segments made of consecutive bars, independent of the display resolution
BARS_PER_SEGMENT = round(1 / BAR_SECONDS)
HISTORY_SECONDS = 120 # Keep last 2 minutes
MAX_BARS = round(HISTORY_SECONDS / BAR_SECONDS)
PLAYBACK_CONTEXT_BARS = round(2 / BAR_SECONDS) # Clicking a bar plays 2 s before and after it
CANVAS_WIDTH = 960
CANVAS_HEIGHT = 150
BAR_WIDTH = CANVAS_WIDTH / MAX_BARS
GUI_UPDATE_INTERVAL_MS = 100 # How often to update the GUI
# Volume of a bar/segment = loudest per-chunk RMS (~23 ms window) within it.
# A single click is too short to raise the RMS much, while a snore is not.
DEFAULT_WAKEUP_VOLUME_THRESHOLD = 0.02 # Default volume level for a segment to count as loud
MIN_WAKEUP_VOLUME_THRESHOLD = 0.001
MAX_WAKEUP_VOLUME_THRESHOLD = 1.0
THRESHOLD_STEP_RATIO = 1.1 # Each mouse wheel step multiplies/divides the threshold by this
# Snoring repeats with each breath, so wake up only when it is sustained:
# at least TRIGGER_MIN_LOUD_SEGMENTS loud segments among the last TRIGGER_WINDOW_SEGMENTS.
TRIGGER_WINDOW_SEGMENTS = 15
TRIGGER_MIN_LOUD_SEGMENTS = 3
# Bars are drawn in dBFS, from DISPLAY_MIN_DBFS (bottom) to 0 dBFS (top)
DISPLAY_MIN_DBFS = -60.0
# Bar colors by volume relative to the threshold: (upper bound of volume/threshold, color)
VOLUME_COLOR_BANDS = ((0.2, "green"), (0.6, "cyan"), (1.0, "yellow"), (4.0, "orange"))
LOUDEST_VOLUME_COLOR = "red"
WAKEUP_SOUND_PATH = Path(__file__).resolve().parent.parent / "materials" / "audio" / "wakeup.m4a"
WAKEUP_SOUND_TIMEOUT_SECONDS = 10
# Players that can decode m4a, in order of preference
SOUND_PLAYER_COMMANDS = (
    ["afplay"],
    ["mpv", "--no-video", "--really-quiet"],
    ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"],
)


def chunk_rms(data: bytes) -> float:
    """Returns the RMS of 16-bit PCM audio data, normalized to 0.0-1.0."""
    samples = np.frombuffer(data, dtype=np.int16) / 32768.0
    return float(np.sqrt(np.mean(np.square(samples)))) if samples.size > 0 else 0.0


def volume_to_dbfs(volume: float) -> float:
    """Converts a normalized volume (0.0-1.0) to dBFS, floored at DISPLAY_MIN_DBFS."""
    return max(DISPLAY_MIN_DBFS, 20 * np.log10(volume)) if volume > 0 else DISPLAY_MIN_DBFS


def volume_to_canvas_y(volume: float) -> float:
    """Maps a normalized volume to a canvas y coordinate (0 dBFS at the top)."""
    return CANVAS_HEIGHT * volume_to_dbfs(min(volume, 1.0)) / DISPLAY_MIN_DBFS


def volume_color(volume: float, threshold: float) -> str:
    """Picks a bar color from how loud the volume is relative to the threshold."""
    ratio = volume / threshold
    for upper_ratio, color in VOLUME_COLOR_BANDS:
        if ratio < upper_ratio:
            return color
    return LOUDEST_VOLUME_COLOR


def find_sound_player_command() -> list[str] | None:
    """Returns the first available command that can play an m4a file, or None."""
    for command in SOUND_PLAYER_COMMANDS:
        if shutil.which(command[0]):
            return command
    return None


class IbikiMonitorApp:
    """
    A Tkinter application to monitor audio input, display volume history,
    and allow playback of recorded segments.
    """
    def __init__(self, master):
        """Initialize the application."""
        self.master = master
        self.master.title("GUI ibiki Monitor")

        # --- Application State ---
        self.audio_queue = queue.Queue()
        self.history_data = deque(maxlen=MAX_BARS) # Stores (timestamp, volume, audio_data_bytes) per bar
        self.pyaudio_instance = None
        self.audio_stream = None
        self.recording_thread = None
        self.stop_event = threading.Event()
        self.playback_pyaudio = None # Separate instance for playback
        self.wakeup_player_command = None # Command prefix used to play the wakeup sound
        # Set by any thread when the wakeup sound cannot be played; shown until the app closes
        self.wakeup_error: str | None = None
        self.recent_loud_count = 0 # Loud segments in the current trigger window (for display)
        self.monitoring_start_time = None # Time when monitoring started
        self.wakeup_volume_threshold = DEFAULT_WAKEUP_VOLUME_THRESHOLD # Initialize the instance variable

        # --- Setup GUI ---
        self.setup_gui()
        self._prepare_wakeup_sound()

        # --- Start Audio Processing ---
        self.start_audio_processing()

        # --- Handle Closing ---
        self.master.protocol( "WM_DELETE_WINDOW", self.on_closing)

        # --- Start GUI Update Loop ---
        self.master.after(GUI_UPDATE_INTERVAL_MS, self.update_graph)

    def setup_gui(self):
        """Creates the GUI elements."""
        self.canvas = tk.Canvas(self.master, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg="white")
        self.canvas.pack(pady=10, padx=10)

        self.device_label = ttk.Label(self.master, text="Monitoring Device: Initializing...")
        self.device_label.pack(pady=2)

        self.status_label = ttk.Label(self.master, text="Initializing...")
        self.status_label.pack(pady=2)

        self.threshold_label = ttk.Label(self.master)
        self.threshold_label.pack(pady=2)
        self._update_threshold_label()

        self.error_label = ttk.Label(self.master, foreground="red")
        self.error_label.pack(pady=2)

        # Bind mouse wheel event to the canvas
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel) # For Windows and macOS
        self.canvas.bind("<Button-4>", self._on_mouse_wheel) # For Linux (scroll up)
        self.canvas.bind("<Button-5>", self._on_mouse_wheel) # For Linux (scroll down)
        # Bars are too thin to click individually, so map the click position to a bar
        self.canvas.bind("<Button-1>", lambda event: self.play_audio(int(event.x // BAR_WIDTH)))


    def _on_mouse_wheel(self, event):
        """Handles mouse wheel events to adjust the threshold."""
        # Determine scroll direction and adjust threshold
        # event.delta is for Windows/macOS, event.num is for Linux
        # Multiplicative steps keep the low range (where snoring usually is) fine-grained
        if event.delta > 0 or event.num == 4: # Scroll up
            self.wakeup_volume_threshold *= THRESHOLD_STEP_RATIO # Increase threshold
        elif event.delta < 0 or event.num == 5: # Scroll down
            self.wakeup_volume_threshold /= THRESHOLD_STEP_RATIO # Decrease threshold

        self.wakeup_volume_threshold = max(MIN_WAKEUP_VOLUME_THRESHOLD,
                                           min(MAX_WAKEUP_VOLUME_THRESHOLD, self.wakeup_volume_threshold))

        print(f"Threshold adjusted to: {self.wakeup_volume_threshold:.4f}")
        self._update_threshold_label()

        # Redraw the canvas to update the threshold line and bar colors
        self._redraw_canvas()

    def _update_threshold_label(self):
        """Shows the current threshold in the GUI."""
        threshold = self.wakeup_volume_threshold
        self.threshold_label.config(
            text=f"Threshold: {threshold:.4f} ({volume_to_dbfs(threshold):.1f} dBFS) - scroll on the graph to adjust")

    def _report_wakeup_error(self, message: str):
        """Records a wakeup sound failure so it stays visible in the GUI."""
        print(f"Error: {message}", file=sys.stderr)
        self.wakeup_error = f"[{time.strftime('%H:%M:%S')}] Wakeup sound unavailable: {message}"

    def _prepare_wakeup_sound(self):
        """Checks that the wakeup sound file and a player for it are available."""
        if not WAKEUP_SOUND_PATH.is_file():
            self._report_wakeup_error(f"file not found: {WAKEUP_SOUND_PATH}")
            return
        self.wakeup_player_command = find_sound_player_command()
        if self.wakeup_player_command is None:
            players = ", ".join(command[0] for command in SOUND_PLAYER_COMMANDS)
            self._report_wakeup_error(f"no sound player found (tried {players})")
            return
        print(f"Wakeup sound: {' '.join(self.wakeup_player_command)} {WAKEUP_SOUND_PATH}")

    def _play_wakeup_sound_thread(self):
        """Target function for the wakeup thread - plays the sound with an external player."""
        if self.wakeup_player_command is None:
            return # Already reported by _prepare_wakeup_sound
        try:
            result = subprocess.run([*self.wakeup_player_command, str(WAKEUP_SOUND_PATH)],
                                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.PIPE, text=True,
                                    timeout=WAKEUP_SOUND_TIMEOUT_SECONDS)
        except (OSError, subprocess.TimeoutExpired) as e:
            self._report_wakeup_error(str(e))
            return
        if result.returncode != 0:
            detail = result.stderr.strip() or f"exit status {result.returncode}"
            self._report_wakeup_error(f"{self.wakeup_player_command[0]} failed: {detail}")

    def start_audio_processing(self):
        """Initializes PyAudio and starts the recording thread."""
        try:
            self.pyaudio_instance = pyaudio.PyAudio()

            # Get default input device info
            device_info = self.pyaudio_instance.get_default_input_device_info()
            input_device_index = int(device_info['index'])
            device_name = device_info['name']

            self.audio_stream = self.pyaudio_instance.open(format=FORMAT,
                                                            channels=CHANNELS,
                                                            rate=RATE,
                                                            input=True,
                                                            frames_per_buffer=CHUNK,
                                                            input_device_index=input_device_index)

            self.stop_event.clear()
            self.recording_thread = threading.Thread(target=self._audio_processor_thread, daemon=True)
            self.recording_thread.start()
            self.monitoring_start_time = time.time() # Record start time
            self.device_label.config(text=f"Monitoring Device: {device_name}") # Display device name in new label
            self.status_label.config(text="Monitoring...") # Keep status label for monitoring time
            print(f"Audio stream opened and recording thread started using device: {device_name}")

        except Exception as e:
            print(f"Error starting audio processing: {e}", file=sys.stderr)
            self.status_label.config(text=f"Error: {e}")
            # Optionally disable features or close app

    def _audio_processor_thread(self):
        """
        Thread target function to continuously read audio, put bars into the
        queue, and judge wakeup on segments of BARS_PER_SEGMENT bars.
        """
        bar_frames = []
        bar_chunk_volumes = []
        segment_bar_volumes = []
        recent_loud_flags = deque(maxlen=TRIGGER_WINDOW_SEGMENTS)

        while not self.stop_event.is_set():
            try:
                # Check if stream is still active (might be closed during shutdown)
                if not self.audio_stream or not self.audio_stream.is_active():
                    print("Audio stream is not active. Exiting audio thread.")
                    break

                data = self.audio_stream.read(CHUNK, exception_on_overflow=False)
                bar_frames.append(data)
                bar_chunk_volumes.append(chunk_rms(data))
                if len(bar_frames) < CHUNKS_PER_BAR:
                    continue

                # Process the completed bar
                bar_volume = max(bar_chunk_volumes)
                # Put raw audio data bytes into the queue for the GUI thread
                self.audio_queue.put((time.time(), bar_volume, b''.join(bar_frames)))
                bar_frames = []
                bar_chunk_volumes = []

                segment_bar_volumes.append(bar_volume)
                if len(segment_bar_volumes) < BARS_PER_SEGMENT:
                    continue

                # --- Wakeup Sound Logic (per segment) ---
                segment_volume = max(segment_bar_volumes)
                segment_bar_volumes = []
                recent_loud_flags.append(segment_volume >= self.wakeup_volume_threshold)
                if sum(recent_loud_flags) >= TRIGGER_MIN_LOUD_SEGMENTS:
                    print(f"{TRIGGER_MIN_LOUD_SEGMENTS} loud segments within {TRIGGER_WINDOW_SEGMENTS} s "
                          f"(threshold {self.wakeup_volume_threshold:.4f}). Playing wakeup sound.")
                    threading.Thread(target=self._play_wakeup_sound_thread, daemon=True).start()
                    # Require sustained snoring again before the next wakeup
                    recent_loud_flags.clear()
                self.recent_loud_count = sum(recent_loud_flags)
                # --- End Wakeup Sound Logic ---

            except IOError as e:
                if e.errno == pyaudio.paInputOverflowed:
                    print("Input overflowed. Skipping.", file=sys.stderr)
                # Handle stream closed error during shutdown gracefully
                elif "Stream closed" in str(e) and self.stop_event.is_set():
                     print("Stream closed during shutdown.")
                     break
                else:
                    print(f"Audio read error: {e}", file=sys.stderr)
                    time.sleep(0.1) # Avoid busy-waiting on error
            except Exception as e:
                # Avoid printing errors if we are shutting down
                if not self.stop_event.is_set():
                    print(f"Unexpected error in audio thread: {e}", file=sys.stderr)
                    time.sleep(0.1)

        # --- Cleanup ---
        print("Audio thread: Stopping audio stream...")
        if self.audio_stream and self.audio_stream.is_active():
            try:
                self.audio_stream.stop_stream()
            except Exception as e:
                print(f"Audio thread: Error stopping stream: {e}", file=sys.stderr)
        if self.audio_stream:
            try:
                self.audio_stream.close()
                print("Audio thread: Audio stream closed.")
            except Exception as e:
                 print(f"Audio thread: Error closing stream: {e}", file=sys.stderr)
        # PyAudio instance termination is handled in on_closing

    def update_graph(self):
        """Processes data from the queue and updates the canvas."""
        try:
            processed_new_data = False
            while not self.audio_queue.empty():
                timestamp, volume, audio_bytes = self.audio_queue.get_nowait()
                self.history_data.append((timestamp, volume, audio_bytes))
                processed_new_data = True

            if processed_new_data:
                self._redraw_canvas()

            # Update status label with timer if monitoring started
            if self.monitoring_start_time:
                elapsed_seconds = int(time.time() - self.monitoring_start_time)
                minutes = elapsed_seconds // 60
                seconds = elapsed_seconds % 60
                self.status_label.config(
                    text=f"Monitoring... {minutes:02d}:{seconds:02d}  "
                         f"(loud {self.recent_loud_count}/{TRIGGER_MIN_LOUD_SEGMENTS} in last {TRIGGER_WINDOW_SEGMENTS} s)")

            self.error_label.config(text=self.wakeup_error or "")

        except queue.Empty:
            pass
        except Exception as e:
            print(f"Error updating graph: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()


        # Schedule the next update if the app is not closing
        if not self.stop_event.is_set():
            self.master.after(GUI_UPDATE_INTERVAL_MS, self.update_graph)

    def _redraw_canvas(self):
        """Clears and redraws the entire canvas based on history_data."""
        self.canvas.delete("all") # Clear canvas

        # Draw the threshold line
        threshold_y = volume_to_canvas_y(self.wakeup_volume_threshold)
        self.canvas.create_line(0, threshold_y, CANVAS_WIDTH, threshold_y, fill="blue", dash=(4, 2), tags="threshold_line")

        # Draw bars for current history (no outline: bars are only a few pixels wide)
        for i, (_, vol, _) in enumerate(self.history_data):
            x0 = i * BAR_WIDTH
            y0 = CANVAS_HEIGHT
            x1 = (i + 1) * BAR_WIDTH
            y1 = volume_to_canvas_y(vol)
            color = volume_color(vol, self.wakeup_volume_threshold)
            self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="", tags="volume_bar")

    def play_audio(self, clicked_index: int):
        """
        Plays the clicked bar together with PLAYBACK_CONTEXT_BARS bars before
        and after it, in a separate thread.
        """
        segments_to_play_bytes = []

        # Make a copy to avoid race conditions if history_data is modified while iterating
        history_list = list(self.history_data)

        if not 0 <= clicked_index < len(history_list):
            return # Clicked on the empty part of the graph

        start_index = max(0, clicked_index - PLAYBACK_CONTEXT_BARS)
        end_index = min(len(history_list), clicked_index + PLAYBACK_CONTEXT_BARS + 1)
        indices_to_play = list(range(start_index, end_index))

        # Collect audio data bytes for the selected segments
        print(f"Attempting to play segments at indices: {indices_to_play} (target: {clicked_index})")
        for index in indices_to_play:
            try:
                ts, vol, audio_bytes = history_list[index]
                if audio_bytes: # Ensure data is not None or empty
                    segments_to_play_bytes.append(audio_bytes)
                    print(f"  - Added segment {index} (ts: {ts:.2f}, vol: {vol:.3f}, len: {len(audio_bytes)})")
                else:
                    print(f"  - Skipped segment {index} (no audio data)")
            except IndexError:
                 print(f"  - Warning: Index {index} out of bounds for history_list (length {len(history_list)})")


        # Combine the audio data
        combined_audio_data = b''.join(segments_to_play_bytes)

        if not combined_audio_data:
            print("No audio data found for the selected segments.")
            return

        print(f"Queueing {len(segments_to_play_bytes)} segments for playback (total length: {len(combined_audio_data)} bytes)")
        # Use a separate thread for playback to avoid blocking GUI
        playback_thread = threading.Thread(target=self._play_audio_bytes_thread, args=(combined_audio_data,), daemon=True)
        playback_thread.start()

    def _play_audio_bytes_thread(self, audio_data):
        """Target function for the playback thread - plays raw bytes."""
        stream_play = None
        # Initialize playback PyAudio instance if not already done
        # This avoids creating/terminating PyAudio repeatedly
        if self.playback_pyaudio is None:
            try:
                self.playback_pyaudio = pyaudio.PyAudio()
            except Exception as e:
                print(f"Playback Error: Could not initialize PyAudio: {e}", file=sys.stderr)
                return

        try:
            stream_play = self.playback_pyaudio.open(format=FORMAT,
                                                     channels=CHANNELS,
                                                     rate=RATE,
                                                     output=True)

            # Play the audio data
            stream_play.write(audio_data)

            # Wait for stream to finish (important!)
            stream_play.stop_stream()
            print("Finished playing audio segment.")

        except Exception as e:
            print(f"Error playing audio bytes: {e}", file=sys.stderr)
        finally:
            if stream_play:
                try:
                    stream_play.close()
                except Exception as e:
                    print(f"Playback Error: Could not close stream: {e}", file=sys.stderr)
            # Don't terminate playback_pyaudio here; terminate in on_closing

    def on_closing(self):
        """Handles window closing event."""
        print("Close button clicked. Stopping threads and cleaning up...")
        self.stop_event.set() # Signal threads to stop

        # Stop GUI updates
        # (update_graph checks stop_event before scheduling next call)

        # Wait for the audio recording thread to finish
        if self.recording_thread and self.recording_thread.is_alive():
             print("Waiting for audio recording thread to join...")
             self.recording_thread.join(timeout=2) # Reduced timeout
             if self.recording_thread.is_alive():
                 print("Audio recording thread did not join cleanly.", file=sys.stderr)

        # Terminate the main PyAudio instance (used for recording)
        if self.pyaudio_instance:
            print("Terminating main PyAudio instance...")
            try:
                self.pyaudio_instance.terminate()
                print("Main PyAudio instance terminated.")
            except Exception as e:
                 print(f"Error terminating main PyAudio instance: {e}", file=sys.stderr)

        # Terminate the playback PyAudio instance
        if self.playback_pyaudio:
            print("Terminating playback PyAudio instance...")
            try:
                self.playback_pyaudio.terminate()
                print("Playback PyAudio instance terminated.")
            except Exception as e:
                 print(f"Error terminating playback PyAudio instance: {e}", file=sys.stderr)


        print("Destroying window.")
        self.master.destroy()
        print("Application finished.")


# --- Main Execution ---
if __name__ == "__main__":
    root = tk.Tk()
    app = IbikiMonitorApp(root)
    root.mainloop()
