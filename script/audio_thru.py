#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Stream mic input to headphone(or other output devices)

import numpy as np
import pyaudio
from typing import List, TypedDict


class AudioDevice(TypedDict):
    index: int
    name: str


class AudioDevices(TypedDict):
    input: List[AudioDevice]
    output: List[AudioDevice]


def list_devices(p) -> AudioDevices:
    devices: AudioDevices = {"input": [], "output": []}
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    for i in range(numdevices):
        device = p.get_device_info_by_host_api_device_index(0, i)
        deviceItem: AudioDevice = {"index": i, "name": device.get("name")}
        if (device.get('maxInputChannels')) > 0:
            devices["input"].append(deviceItem)
        if (device.get('maxOutputChannels')) > 0:
            devices["output"].append(deviceItem)
    return devices


def get_volume(data: bytes) -> float:
    x = np.frombuffer(data, dtype="int16") / 32768.0
    return x.max()


# 基本パラメータ設定
CHUNK = 2048  # ブロックサイズ
FORMAT = pyaudio.paInt16  # 16ビットフォーマット
CHANNELS = 1  # モノラル
RATE = 44100 // 2  # サンプルレート

p = pyaudio.PyAudio()

devices = list_devices(p)

# ユーザーに入力と出力デバイスを選んでもらう
print("--- Input ---")
for device in devices["input"]:
    print(f"{device['index']}: {device['name']}")
input_device = int(input("Enter the device ID for input: "))

print("--- Output ---")
for device in devices["output"]:
    print(f"{device['index']}: {device['name']}")
output_device = int(input("Enter the device ID for output: "))

# 入力デバイスの設定
stream_in = p.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    input=True,
    frames_per_buffer=CHUNK,
    input_device_index=input_device
)

# 出力デバイスの設定
stream_out = p.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    output=True,
    frames_per_buffer=CHUNK,
    output_device_index=output_device
)

print('Streaming...')


def get_graph_char(volume: float) -> str:
    graph_char = "▁▂▃▄▅▆▇█"
    i = int(volume * 1000) // 10
    i = min(i, len(graph_char) - 1)
    return graph_char[i]


while True:
    try:
        data = stream_in.read(CHUNK)
        stream_out.write(data)
        volume = get_volume(data)
        print(get_graph_char(volume), end="", flush=True)
    except OSError as e:
        if e.errno == -9981:
            print("X", end="", flush=True)
        else:
            raise e
    except KeyboardInterrupt:
        break

print('Finished recording')

# ストリームを閉じる
stream_in.stop_stream()
stream_in.close()
stream_out.stop_stream()
stream_out.close()

# PyAudioを閉じる
p.terminate()
