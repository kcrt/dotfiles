#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
#
# Realtime speech recognition with whisper
#
# Ref.: https://github.com/mallorbc/whisper_mic

# require: pydub whisper-openai
# Usage: python3 whisper_mic.py --model large

import whisper
import queue
import threading
import pyaudio
import tempfile
import numpy as np
import wave
import os
import argparse
import sys

AUDIO_THRESHOLD = 0.03
temp_dir = tempfile.mkdtemp()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, default='large',
                        help='model name', choices=['tiny', 'base', 'small', 'medium', 'large', 'tiny.en', 'base.en', 'small.en', 'medium.en'])
    parser.add_argument('--language', type=str, default='ja')
    parser.add_argument('--translate', action="store_true",
                        default=False, help="translate to English")
    parser.add_argument('-i', '--input-device-index', type=int, default=None,
                        help='input device index (default: None), set -1 to list devices')

    return parser.parse_args()


def main():

    args = parse_args()

    if args.input_device_index == -1:
        p = pyaudio.PyAudio()
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            print(
                f"Device #{i}: {info['name']} (in: {info['maxInputChannels']}, out: {info['maxOutputChannels']})")
        exit()

    print("Loading...", file=sys.stderr)
    audio_model = whisper.load_model(args.model)
    audio_queue = queue.Queue()
    result_queue = queue.Queue()

    print("--- Start ---", file=sys.stderr)
    threading.Thread(target=record_audio,
                     args=(audio_queue, args.input_device_index)).start()
    threading.Thread(target=transcribe_audio,
                     args=(audio_queue, result_queue, audio_model, args.language, args.translate)).start()
    while True:
        print(result_queue.get())


def record_audio(audio_queue, input_device_index=None):

    p = pyaudio.PyAudio()
    audio_data = []

    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    frames_per_buffer=1024,
                    input_device_index=input_device_index
                    )

    is_recording = False
    while True:
        chunk = stream.read(4096)
        # detect if the audio is above the threshold
        chunk_data = np.frombuffer(
            chunk, dtype="int16") / 32768.0    # 0.0 - 1.0
        volume = chunk_data.max()
        if is_recording:
            if volume < AUDIO_THRESHOLD:
                # stop recording and send the audio data to the queue
                is_recording = False
                audio_queue.put(b''.join(audio_data))
                audio_data = []
            else:
                audio_data.append(chunk)
        else:
            if volume > AUDIO_THRESHOLD:
                is_recording = True
                audio_data.append(chunk)


def transcribe_audio(audio_queue, result_queue, audio_model, language, translate):
    task = "translate" if translate else "transcribe"
    while True:
        audio_data = audio_queue.get()
        temp_filename = tempfile.mktemp(suffix='.wav', dir=temp_dir)
        with wave.open(temp_filename, 'wb') as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(16000)
            f.writeframes(audio_data)
        result = audio_model.transcribe(
            temp_filename, fp16=False, language=language, task=task)
        result_queue.put(result["text"])
        os.remove(temp_filename)


if __name__ == '__main__':
    main()
