#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# require: pandas, Faker, and tqdm

import sys
import pandas as pd
import random
from faker import Faker
from random import randrange
from datetime import datetime
from tqdm import tqdm
import argparse
import csv
import csv


def parse_args():

    parser = argparse.ArgumentParser(
        description="Generate dummy data of patients")
    parser.add_argument("-n", type=int, default=100,
                        help='Number of patients')
    parser.add_argument("--lang", type=str, default="ja_JP",
                        help="Language of fake data")
    return parser.parse_args()


def main():
    args = parse_args()
    fake = Faker(args.lang)

    writer = None
    for i in tqdm(range(args.n + 1)):
        birthday = fake.date_of_birth(minimum_age=0, maximum_age=90)
        sex = random.choice(["M", "F"])
        name = fake.name_male() if sex == "M" else fake.name_female()
        age = (datetime.now().date() - birthday).days / 365.25

        patient = {
            "id": i,
            "name": name,
            "sex": sex,
            "age": age,
            "birthday": birthday,
            "address": fake.address(),
            "patientid": fake.ean(length=8),
            "company": fake.company() if age > 18 else "",
            "username": fake.user_name(),
            "email": fake.email()
        }
        if writer == None:
            writer = csv.DictWriter(sys.stdout, fieldnames=patient.keys())
            writer.writeheader()
        writer.writerow(patient)


if __name__ == '__main__':
    main()
