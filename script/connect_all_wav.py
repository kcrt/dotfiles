#!/usr/bin/env python3

# Connect all WAV files in a directory into one WAV file, separated by 3 seconds of silence
# Needs: pydub (pip install pydub)

import os
from pydub import AudioSegment
import tqdm

SILENCE_DURATION = 2000  # Duration in milliseconds

# Define the directory containing the WAV files
directory = "."  # Replace with the path to your directory

# Scan the directory for all WAV files and sort them
wav_files = sorted([os.path.join(directory, f)
                   for f in os.listdir(directory) if f.endswith('.wav')])

# Create a 3-second silence audio segment, with parameters for stereo and sample rate
silence_mono = AudioSegment.silent(
    duration=SILENCE_DURATION)  # Duration in milliseconds
silence_stereo = silence_mono.set_channels(2)
silence_mono = silence_mono.set_frame_rate(48000)
silence_stereo = silence_stereo.set_frame_rate(48000)

# Initialize an empty audio segment to store the concatenated result
output = AudioSegment.silent(duration=0, frame_rate=48000)

# Read and concatenate each file with silence in between
for wav_file in tqdm.tqdm(wav_files):
    audio = AudioSegment.from_file(wav_file)

    # Check if the audio is mono or stereo and concatenate accordingly
    if audio.channels == 1:
        output += audio + silence_mono
    else:
        output += audio + silence_stereo

# Remove the last silence
output = output[:-SILENCE_DURATION]

# Save the concatenated result to a new WAV file
output.export("output.wav", format="wav")
