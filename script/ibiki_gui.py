#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk
import pyaudio
import numpy as np
import threading
import time
import datetime
from collections import deque
import queue
import sys
import os

# --- Constants ---
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS_PER_SEGMENT = 1  # How long each segment/bar represents
MAX_SEGMENTS = 120 # Keep last 2 minutes (120 seconds * 1 segment/second)
CANVAS_WIDTH = 800
CANVAS_HEIGHT = 150
BAR_WIDTH = CANVAS_WIDTH / MAX_SEGMENTS
GUI_UPDATE_INTERVAL_MS = 100 # How often to update the GUI
WAKEUP_VOLUME_THRESHOLD = 0.05 # Volume level to trigger wakeup sound

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
        self.history_data = deque(maxlen=MAX_SEGMENTS) # Stores (timestamp, max_volume, audio_data_bytes)
        self.canvas_items = {} # Maps timestamp to (canvas_item_id, audio_data_bytes, volume)
        self.pyaudio_instance = None
        self.audio_stream = None
        self.recording_thread = None
        self.stop_event = threading.Event()
        self.playback_pyaudio = None # Separate instance for playback
        self.last_wakeup_time = 0 # Track when the wakeup sound was last played

        # --- Setup GUI ---
        self.setup_gui()

        # --- Start Audio Processing ---
        self.start_audio_processing()

        # --- Handle Closing ---
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        # --- Start GUI Update Loop ---
        self.master.after(GUI_UPDATE_INTERVAL_MS, self.update_graph)

    def setup_gui(self):
        """Creates the GUI elements."""
        self.canvas = tk.Canvas(self.master, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg="white")
        self.canvas.pack(pady=10, padx=10)

        self.status_label = ttk.Label(self.master, text="Initializing...")
        self.status_label.pack(pady=5)

    def start_audio_processing(self):
        """Initializes PyAudio and starts the recording thread."""
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            self.audio_stream = self.pyaudio_instance.open(format=FORMAT,
                                                            channels=CHANNELS,
                                                            rate=RATE,
                                                            input=True,
                                                            frames_per_buffer=CHUNK)
            self.stop_event.clear()
            self.recording_thread = threading.Thread(target=self._audio_processor_thread, daemon=True)
            self.recording_thread.start()
            self.status_label.config(text="Monitoring...")
            print("Audio stream opened and recording thread started.")
        except Exception as e:
            print(f"Error starting audio processing: {e}", file=sys.stderr)
            self.status_label.config(text=f"Error: {e}")
            # Optionally disable features or close app

    def _audio_processor_thread(self):
        """
        Thread target function to continuously read audio and put segments
        into the queue.
        """
        segment_frames = []
        segment_start_time = time.time()

        while not self.stop_event.is_set():
            try:
                # Check if stream is still active (might be closed during shutdown)
                if not self.audio_stream or not self.audio_stream.is_active():
                    print("Audio stream is not active. Exiting audio thread.")
                    break

                data = self.audio_stream.read(CHUNK, exception_on_overflow=False)
                segment_frames.append(data)

                current_time = time.time()
                if current_time - segment_start_time >= RECORD_SECONDS_PER_SEGMENT:
                    # Process the completed segment
                    audio_data_segment = b''.join(segment_frames)
                    # Ensure data is not empty before processing
                    if audio_data_segment:
                        x = np.frombuffer(audio_data_segment, dtype=np.int16) / 32768.0
                        max_volume = np.max(np.abs(x)) if len(x) > 0 else 0.0
                    else:
                        max_volume = 0.0
                        print("Warning: Empty audio segment detected.")

                    # --- Wakeup Sound Logic ---
                    if max_volume >= WAKEUP_VOLUME_THRESHOLD:
                        now = time.time()
                        if now - self.last_wakeup_time > 2:
                            print(f"Volume threshold exceeded ({max_volume:.3f} >= {WAKEUP_VOLUME_THRESHOLD}). Playing wakeup sound.")
                            # Use absolute path for afplay
                            os.system("/usr/bin/afplay /Users/kcrt/dotfiles/audio/wakeup.m4a &")
                            self.last_wakeup_time = now
                    # --- End Wakeup Sound Logic ---

                    # Put raw audio data bytes into the queue for the GUI thread
                    self.audio_queue.put((current_time, max_volume, audio_data_segment))

                    # Start new segment
                    segment_frames = []
                    segment_start_time = current_time

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
                timestamp, max_volume, audio_bytes = self.audio_queue.get_nowait()
                self.history_data.append((timestamp, max_volume, audio_bytes))
                processed_new_data = True

            # Only redraw if there's new data or the history isn't full yet
            # (to handle initial population)
            if processed_new_data or len(self.canvas_items) < len(self.history_data):
                self._redraw_canvas()

        except queue.Empty:
            pass # No new data
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
        new_canvas_items = {} # Build the new mapping

        # Clean up old items from the internal mapping first
        # Get current timestamps from history
        current_timestamps = {ts for ts, _, _ in self.history_data}
        # Remove items from canvas_items whose timestamps are no longer in history
        keys_to_remove = set(self.canvas_items.keys()) - current_timestamps
        for ts_key in keys_to_remove:
            del self.canvas_items[ts_key]
            # Actual canvas item deleted by canvas.delete("all")

        # Draw the threshold line
        threshold_y = CANVAS_HEIGHT - CANVAS_HEIGHT * np.sqrt(min(WAKEUP_VOLUME_THRESHOLD, 1.0))
        self.canvas.create_line(0, threshold_y, CANVAS_WIDTH, threshold_y, fill="blue", dash=(4, 2), tags="threshold_line")

        # Draw bars for current history
        for i, (ts, vol, audio_data) in enumerate(self.history_data):
            x0 = i * BAR_WIDTH
            y0 = CANVAS_HEIGHT
            x1 = (i + 1) * BAR_WIDTH
            # Scale volume (0.0 to 1.0) to canvas height using sqrt
            bar_height = CANVAS_HEIGHT * np.sqrt(min(vol, 1.0))
            y1 = CANVAS_HEIGHT - bar_height

            # Determine color based on volume thresholds
            if vol < 0.01: color = "green"
            elif vol < 0.03: color = "cyan"
            elif vol < 0.05: color = "yellow"
            elif vol < 0.2: color = "orange"
            else: color = "red"

            bar_id = self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="black", tags="volume_bar")
            # Use lambda with default argument capture for correct data binding
            # Pass timestamp instead of raw audio data
            self.canvas.tag_bind(bar_id, "<Button-1>", lambda event, timestamp=ts: self.play_audio(timestamp))
            new_canvas_items[ts] = (bar_id, audio_data, vol) # Store timestamp, item_id, audio_bytes, volume

        self.canvas_items = new_canvas_items # Update the global mapping

    def play_audio(self, clicked_timestamp):
        """
        Finds the audio segment corresponding to the clicked timestamp,
        its preceding and succeeding segments, concatenates their audio data,
        and plays it in a separate thread.
        """
        # Find the index and data of the clicked segment
        clicked_index = -1
        segments_to_play_bytes = []

        # Convert deque to list for easier indexing (deque doesn't support direct indexing efficiently)
        # Make a copy to avoid race conditions if history_data is modified while iterating
        history_list = list(self.history_data)

        for i, (ts, _, _) in enumerate(history_list):
            if ts == clicked_timestamp:
                clicked_index = i
                break

        if clicked_index == -1:
            print(f"Error: Could not find segment with timestamp {clicked_timestamp}")
            return

        # Determine indices of segments to play (previous, current, next)
        indices_to_play = []
        if clicked_index > 0: # Check if previous exists
            indices_to_play.append(clicked_index - 1)
        indices_to_play.append(clicked_index)
        if clicked_index < len(history_list) - 1: # Check if next exists
            indices_to_play.append(clicked_index + 1)

        # Collect audio data bytes for the selected segments
        print(f"Attempting to play segments at indices: {indices_to_play}")
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
