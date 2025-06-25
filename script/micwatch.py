#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "matplotlib",
#     "numpy",
#     "pyaudio",
# ]
# ///

import pyaudio
import numpy as np
import matplotlib.pyplot as plt

RATE = 12000
CHUNK = 1024
FORMAT = pyaudio.paFloat32
CHANNELS = 1

pa = pyaudio.PyAudio()
stream = pa.open(rate=RATE, channels=CHANNELS, format=FORMAT,
                 input=True, frames_per_buffer=CHUNK)

plt.show(block=False)
fig = plt.figure(figsize=(15,3))
while True:
    d = stream.read(CHUNK)
    d = np.frombuffer(d, dtype=np.float32)
    # d = np.log10(np.abs(d))
    fft_ret = np.fft.fft(d, norm="ortho")
    # freq = np.fft.fftfreq(d.astype(np.int32) * 1024)

    plt.cla()
    plt.xlim(0, 1024)
    plt.ylim(-0.1, 0.1)
    plt.plot(d)
    plt.pause(0.001)
