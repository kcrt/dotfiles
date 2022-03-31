#!/usr/bin/env python3

# require pyaudio, numpy, pychalk

import time
import pyaudio
import numpy as np
import os
import datetime
import chalk 

# 音データフォーマット
chunk = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 2

# 音の取込開始
p = pyaudio.PyAudio()
stream = p.open(format = FORMAT,
    channels = CHANNELS,
    rate = RATE,
    input = True,
    frames_per_buffer = chunk
)

cnt = 0
lastwakeup = 0

while True:
    # 音データの取得
    data = stream.read(chunk)
    # ndarrayに変換
    x = np.frombuffer(data, dtype="int16") / 32768.0

    xmax = x.max()
    if xmax < 0.01:
        print(chalk.green("*"), end="", flush=True)
    elif xmax < 0.03:
        print(chalk.cyan("*"), end="", flush=True)
    elif xmax < 0.05:
        print(chalk.yellow("*"), end="", flush=True)
    else:
        print(chalk.red("*", bold=xmax>0.2), end="", flush=True)
        if time.time() - lastwakeup > 2:
            os.system("/usr/bin/say \"wake up\" &")
            lastwakeup = time.time()

    cnt += 1
    if cnt == 60:
        nowvar = datetime.datetime.now()
        print("")
        print(f"[{nowvar.hour:02}:{nowvar.minute:02}:{nowvar.second:02}] ", end="")
        cnt = 0

stream.close()
p.terminate()

