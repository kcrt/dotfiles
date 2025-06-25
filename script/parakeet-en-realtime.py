#!/usr/bin/env -S uv run
# /// script
# requires-python = "==3.10"
# dependencies = [
#     "numpy",
#     "parakeet-mlx",
#     "pyaudio",
#     "matplotlib",
#     "tkinter==8.6.16
# ,
# ]
# ///

# -*- coding: utf-8 -*-

import os
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
import numpy as np
import pyaudio
from parakeet_mlx import from_pretrained
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque
import time

class RealtimeTranscriptionGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Real-time Speech Transcription")
        self.root.geometry("800x600")
        
        # Audio parameters
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paFloat32
        self.CHANNELS = 1
        self.RATE = 16000
        
        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.recording = False
        
        # Initialize model
        self.model = None
        self.transcriber = None
        
        # Audio buffer for visualization
        self.audio_buffer = deque(maxlen=self.RATE * 5)  # 5 seconds buffer
        
        # Queue for thread communication
        self.audio_queue = queue.Queue()
        self.transcription_queue = queue.Queue()
        
        self.setup_ui()
        self.load_model()
    
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Control frame
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        # Start/Stop button
        self.record_button = ttk.Button(control_frame, text="Start Recording", command=self.toggle_recording)
        self.record_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Status label
        self.status_label = ttk.Label(control_frame, text="Ready")
        self.status_label.pack(side=tk.LEFT)
        
        # Paned window for audio and text
        paned_window = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        paned_window.grid(row=1, column=0, sticky="nsew")
        
        # Audio waveform frame
        audio_frame = ttk.LabelFrame(paned_window, text="Audio Waveform", padding="5")
        paned_window.add(audio_frame, weight=1)
        
        # Create matplotlib figure for waveform
        self.fig, self.ax = plt.subplots(figsize=(8, 3))
        self.ax.set_ylim(-1, 1)
        self.ax.set_xlim(0, self.RATE * 2)  # 2 seconds window
        self.line, = self.ax.plot([], [])
        self.ax.set_ylabel('Amplitude')
        self.ax.set_title('Real-time Audio Waveform')
        
        # Embed matplotlib in tkinter
        # self.canvas = FigureCanvasTkAgg(self.fig, audio_frame)
        # self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Transcription text frame
        text_frame = ttk.LabelFrame(paned_window, text="Transcription", padding="5")
        paned_window.add(text_frame, weight=1)
        
        # Text widget for transcription
        self.text_widget = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, height=10)
        self.text_widget.pack(fill=tk.BOTH, expand=True)
    
    def load_model(self):
        self.status_label.config(text="Loading model...")
        self.root.update()
        
        try:
            self.model = from_pretrained("mlx-community/parakeet-tdt-0.6b-v2")
            self.status_label.config(text="Model loaded - Ready")
        except Exception as e:
            self.status_label.config(text=f"Error loading model: {str(e)}")
    
    def toggle_recording(self):
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        if self.model is None:
            self.status_label.config(text="Model not loaded")
            return
        
        self.recording = True
        self.record_button.config(text="Stop Recording")
        self.status_label.config(text="Recording...")
        
        # Start audio stream
        try:
            self.stream = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
                stream_callback=self.audio_callback
            )
            self.stream.start_stream()
            
            # Start transcription thread
            self.transcriber = self.model.transcribe_stream(context_size=(256, 256)).__enter__()
            self.transcription_thread = threading.Thread(target=self.transcription_worker)
            self.transcription_thread.daemon = True
            self.transcription_thread.start()
            
            # Start GUI update timer
            self.update_gui()
            
        except Exception as e:
            self.status_label.config(text=f"Error starting recording: {str(e)}")
            self.recording = False
            self.record_button.config(text="Start Recording")
    
    def stop_recording(self):
        self.recording = False
        self.record_button.config(text="Start Recording")
        self.status_label.config(text="Stopped")
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        if self.transcriber:
            self.transcriber.__exit__(None, None, None)
            self.transcriber = None
    
    def audio_callback(self, in_data, frame_count, time_info, status):
        if self.recording:
            # Convert bytes to numpy array
            audio_data = np.frombuffer(in_data, dtype=np.float32)
            
            # Add to buffer for visualization
            self.audio_buffer.extend(audio_data)
            
            # Add to queue for transcription
            self.audio_queue.put(audio_data.copy())
        
        return (in_data, pyaudio.paContinue)
    
    def transcription_worker(self):
        while self.recording and self.transcriber:
            try:
                # Get audio chunk from queue
                audio_chunk = self.audio_queue.get(timeout=0.1)
                
                # Add to transcriber
                self.transcriber.add_audio(audio_chunk)
                
                # Get current transcription
                result = self.transcriber.result
                if result and result.text:
                    self.transcription_queue.put(result.text)
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Transcription error: {e}")
    
    def update_gui(self):
        if not self.recording:
            return
        
        # Update waveform
        if len(self.audio_buffer) > 0:
            # Get recent audio data
            recent_data = list(self.audio_buffer)[-self.RATE * 2:]  # Last 2 seconds
            if len(recent_data) > 0:
                x = np.arange(len(recent_data))
                self.line.set_data(x, recent_data)
                self.ax.set_xlim(0, len(recent_data))
                self.canvas.draw_idle()
        
        # Update transcription text
        try:
            while True:
                text = self.transcription_queue.get_nowait()
                self.text_widget.delete(1.0, tk.END)
                self.text_widget.insert(tk.END, text)
                self.text_widget.see(tk.END)
        except queue.Empty:
            pass
        
        # Schedule next update
        if self.recording:
            self.root.after(100, self.update_gui)
    
    def __del__(self):
        if self.stream:
            self.stream.close()
        if hasattr(self, 'audio'):
            self.audio.terminate()

def main():

    os.environ['TCL_LIBRARY'] = '/opt/homebrew/Cellar/tcl-tk@8/8.6.16/lib/tcl8.6'
    os.environ['TK_LIBRARY'] = '/opt/homebrew/Cellar/tcl-tk@8/8.6.16/lib/tk8.6'

    root = tk.Tk()
    app = RealtimeTranscriptionGUI(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        if hasattr(app, 'audio'):
            app.audio.terminate()

if __name__ == '__main__':
    main()

