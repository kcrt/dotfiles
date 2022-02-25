#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import glob
import json
import sys
import tensorflow as tf
import numpy as np
from tqdm import tqdm
from PIL import Image
# from PILImageEx import ImageEx
# from keras.models import Sequential
# from keras.layers import Dense, Dropout, Activation, Flatten, Input
# from keras.layers import Conv2D, MaxPooling2D
# from keras.utils import np_utils
# from keras import backend as K
# from keras.preprocessing.image import ImageDataGenerator
# from keras.callbacks import EarlyStopping, ModelCheckpoint
# from sklearn.model_selection import train_test_split
from pathlib import Path
import os
import shutil
import argparse


def load_tflite_dict(model_file):
    txt: str = (Path(model_file).parent / "dict.txt").read_text()
    return txt.rstrip().split("\n")

def get_answerprob(model_answer: [str], probs: [int]) -> [str, float]:
    total = sum(probs)
    most_likely_index = np.argmax(probs)
    return model_answer[most_likely_index], probs[most_likely_index] / total
    

def main():
    parser = argparse.ArgumentParser(description="Recognize images with trained model of tflite")
    parser.add_argument("model", help="model")
    parser.add_argument("images_dir", help="Directory for images to recognize.")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    model = tf.lite.Interpreter(model_path=args.model)
    model.allocate_tensors()
    input_details = model.get_input_details()
    output_details = model.get_output_details()
    _, w, h, c = input_details[0]["shape"]

    model_answer = load_tflite_dict(args.model)

    print("filename\tanswer\tprob")
    for fpath in tqdm(list(Path(args.images_dir).glob("**/*.png"))):
        filename = str(fpath)
        img = Image.open(filename)
        if c == 1:
            img = img.convert("L")
        elif c == 3:
            img = img.convert("RGB")

        img = img.resize((w, h))
        imgnp = np.asarray(img, dtype=np.uint8).reshape(1, w, h, c)
        model.set_tensor(input_details[0]['index'], imgnp)
        model.invoke()

        probs = model.get_tensor(output_details[0]["index"])[0]
        answer, prob = get_answerprob(model_answer, probs)

        print(f"{filename}\t{answer}\t{prob}")

if __name__ == '__main__':
    main()

