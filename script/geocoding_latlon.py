#!/usr/bin/env python3

# get lat/lon from name of place

import os
import argparse
import requests

URL = "https://maps.googleapis.com/maps/api/geocode/json"
API_KEY = os.environ['GOOGLE_MAPS_API_KEY']

def parse_args():
    parser = argparse.ArgumentParser(description='Get lat/lon from name of place')
    parser.add_argument('place', help='name of place')
    return parser.parse_args()


def get_latlon(place):
    params = {
        'address': place,
        'key': API_KEY
    }
    try:
        response = requests.get(URL, params=params)
        data = response.json()
        if data["status"] != "OK":
            print(f"Error: {data['status']}")
            exit(1)
        else:
            loc = data["results"][0]["geometry"]["location"]
            return (loc["lat"], loc["lng"])
    except requests.exceptions.RequestException as e:
        print(e)
        exit(1)

def main():
    args = parse_args()
    latlon = get_latlon(args.place)
    print(f"{args.place}, {latlon[0]}, {latlon[1]}")
    pass


if __name__ == '__main__':
    main()