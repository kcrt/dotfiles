#!/usr/bin/env python3

# Find Google Home and speak a message on it

import argparse
import time
import pychromecast


def parsearg():
    parser = argparse.ArgumentParser(
        description="Say a message on Google Home")
    parser.add_argument("message", help='Message to say', nargs='?')
    parser.add_argument("-n", '--name', help='Name of Google Home device')
    parser.add_argument(
        "-l", '--list', help='List available devices', action='store_true')
    return parser.parse_args()


def main():
    args = parsearg()
    ret = pychromecast.get_chromecasts()
    chromecasts: list[pychromecast.Chromecast] = ret[0]

    if len(chromecasts) == 0:
        print("No Google Home found")
        return

    if args.list:
        for cc in chromecasts:
            print(f"{cc.name} ({cc.model_name})")
        return

    if args.name:
        chromecast = pychromecast.get_chromecast(friendly_name=args.name)
    else:
        chromecast = chromecasts[0]
    print(f"Target device: {chromecast.name}")

    if args.message is None:
        print("No message to say")
        return

    # save message as audio file in temp
    # play audio file on chromecast
    # delete audio file

    chromecast.wait()
    mc = chromecast.media_controller
    print("Playing...")
    mc.play_media(
        "http://files.kcrt.net/say.m4a", "audio/mp4")
    mc.block_until_active()
    # mc.pause()
    mc.play()
    print(mc.status)
    time.sleep(5)

    # chromecast.media_controller.pause()


if __name__ == "__main__":
    main()
