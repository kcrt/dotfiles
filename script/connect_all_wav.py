#!/usr/bin/env python3

# Connect all WAV files in a directory into one WAV file, separated by silence
# Needs: pydub (pip install pydub)

import os
from pydub import AudioSegment
import tqdm
import argparse

def main():
    parser = argparse.ArgumentParser(description="Connect all WAV files in a directory into one WAV file, separated by silence.")
    parser.add_argument('directory', nargs='?', default=".", help="Directory containing the WAV files (default: current directory).")
    parser.add_argument('--silence_duration', type=int, default=2000, help="Duration of silence between WAV files in milliseconds (default: 2000).")
    parser.add_argument('--output_file', default="output.wav", help="Name of the output WAV file (default: output.wav).")
    args = parser.parse_args()

    SILENCE_DURATION = args.silence_duration
    directory = args.directory
    output_filename = args.output_file

    # Scan the directory for all WAV files and sort them
    wav_files = sorted([os.path.join(directory, f)
                       for f in os.listdir(directory) if f.endswith('.wav')])

    if not wav_files:
        print(f"No .wav files found in directory: {directory}")
        return

    # Create a silence audio segment, with parameters for stereo and sample rate
    # Assuming 48000Hz as a common sample rate, adjust if necessary or make it an arg
    silence_mono = AudioSegment.silent(duration=SILENCE_DURATION, frame_rate=48000)
    silence_stereo = silence_mono.set_channels(2) # Ensure stereo silence if any input is stereo

    # Initialize an empty audio segment to store the concatenated result
    output_audio = AudioSegment.silent(duration=0, frame_rate=48000)

    print(f"Processing {len(wav_files)} WAV files from '{directory}'...")
    # Read and concatenate each file with silence in between
    for wav_file in tqdm.tqdm(wav_files):
        try:
            audio = AudioSegment.from_file(wav_file)

            # Match silence channels to audio channels
            if audio.channels == 1:
                current_silence = silence_mono.set_frame_rate(audio.frame_rate)
            else: # audio.channels == 2 or more
                current_silence = silence_stereo.set_frame_rate(audio.frame_rate)
            
            # Ensure output audio matches the first file's sample rate and channels
            if len(output_audio) == 0:
                output_audio = AudioSegment.silent(duration=0, frame_rate=audio.frame_rate)
                if audio.channels == 2:
                    output_audio = output_audio.set_channels(2)

            # Resample audio to match output_audio if necessary
            if audio.frame_rate != output_audio.frame_rate:
                audio = audio.set_frame_rate(output_audio.frame_rate)
            if audio.channels != output_audio.channels:
                audio = audio.set_channels(output_audio.channels)

            output_audio += audio + current_silence
        except Exception as e:
            print(f"Error processing file {wav_file}: {e}")
            continue # Skip to the next file

    if len(output_audio) > SILENCE_DURATION:
        # Remove the last silence
        output_audio = output_audio[:-SILENCE_DURATION]
    elif len(output_audio) == 0 and wav_files:
        print("No audio was successfully processed to output.")
        return


    # Save the concatenated result to a new WAV file
    try:
        output_audio.export(output_filename, format="wav")
        print(f"Successfully created: {output_filename}")
    except Exception as e:
        print(f"Error exporting output file {output_filename}: {e}")

if __name__ == "__main__":
    main()
