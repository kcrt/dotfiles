#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import binascii
import subprocess
import re
import json
import urllib.request
import argparse

# see:
# https://echonet.jp/wp/wp-content/uploads/pdf/General/Standard/AIF/ac/ac_aif_ver1.10.pdf
# https://echonet.jp/wp/wp-content/uploads/pdf/General/Standard/Release/Release_P/Appendix_Release_P_rev1.pdf

# Example 1: Check power status of air conditioner
# $ ./echonetlite.py -i 192.168.0.16 05FF01 013001 62  80
#                                    SEOJ   DEOJ   ESV Prop
#                              Controller   Aircon Get Power
# 1081000101300105ff017201800130
# -> 1081 0001 013001  05FF01      72      01   80    0130
#    EHD  TID  SEOJ    DEOJ        ESV     OPC  Prop  EDT
#              Aircon  Controller  Get_Res 1    Power 01=1 byte, 30 = On
#    = Specified air conditioner (0x013000) is ON (0x30)
#
# Example 2: Fill the bathtub with hot water in automatic mode
# $ ./echonetlite.py -i 192.168.0.15 05FF01 027201 61    E3    41
#                                    SEOJ   DEOJ   ESV   Prop  EDT
#                              Controller   Bath   SetC  Auto  On
# 1081000102720105ff017101e300
# -> 1081 0001 027201  05FF01      71      01   E3    00
#    EHD  TID  SEOJ    DEOJ        ESV     OPC  Prop  EDT
#              Bath    Controller  Set_Res 1    Auto 0 byte
#
# Example 3: Check the current outside temperature
# $ ./echonetlite.py -e int8 -i 192.168.0.16 05FF01 013001 62 BE
# 5
#
# Example 4: Check the temperature of the bathroom
# ./echonetlite.py -e int16/10 -i 192.168.0.15 05FF01 001101 62 E0
# 8.0


""" acquire IPv4 address from MAC address """


def MAC2IPv4(mac):

    ret = subprocess.run(
        f"arp -an | grep {mac} | head -n1", shell=True, capture_output=True)
    output = ret.stdout.decode()
    match = re.search(r"\d+\.\d+\.\d+\.\d+", output)
    if match:
        return match.group()
    else:
        print("Cannot acquire IPv4.")
        exit(-1)


def echonet(targetIP, command):

    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.bind(("0.0.0.0", 3610))

    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send_sock.sendto(bytes.fromhex(command), (targetIP, 3610))

    # receive response with timeout 5 sec
    recv_sock.settimeout(5)
    try:
        data, addr = recv_sock.recvfrom(1024)
    except socket.timeout:
        return ""

    send_sock.close()
    recv_sock.close()
    return data


def decode_1byte(ret):
    if (ret[10] == 0x72 and ret[11] == 0x1):
        return ret[14]
    else:
        return None


def uint8_to_int8(val):
    # 0 - 127 -> 0 - 127
    # 255 -> -1, 254 -> -2, ..., 128 -> -128
    if (val > 128):
        return val - 256
    else:
        return val


def uint16_to_int16(val):
    # 0 - 32767 -> 0 - 32767
    # 65535 -> -1, 65534 -> -2, ..., 32768 -> -32768
    if (val > 32768):
        return val - 65536
    else:
        return val


def convert_edc(hex, mode):
    if hex == "":
        return None

    if mode == 'raw':
        return hex
    elif mode == 'uint8':
        return int(hex, 16)
    elif mode == 'int8':
        return uint8_to_int8(int(hex, 16))
    elif mode == 'uint16':
        return int(hex, 16)
    elif mode == 'int16':
        return uint16_to_int16(int(hex, 16))
    elif mode == 'int16/10':
        return uint16_to_int16(int(hex, 16)) / 10
    elif mode == 'str':
        return bytes.fromhex(hex).decode('utf-8')
    else:
        return None


def parse_args():
    parser = argparse.ArgumentParser(description='Echonetlite')
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose')
    parser.add_argument('-e', '--edc-only',
                        choices=['raw', 'uint8', 'int8', 'uint16', 'int16', 'int16/10', 'str'], help='Print only edc')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-i', '--ip', help='IP address of the target')
    group.add_argument('-m', '--mac', help='MAC address of the target')
    parser.add_argument('seoj', help='SEOJ 送信機器種類 e.g. 05FF01=Controller')
    parser.add_argument('deoj', help='DEOJ 受信機器種類 e.g. 013001=Aircon')
    parser.add_argument('esv', help='ESV Get=62 SetC(Set with answer)=61')
    parser.add_argument(
        'epc', help='Echonet lite property (must be 1 byte) e.g. 80=Power')
    parser.add_argument('edt', help='EDT', nargs='?', default="")
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    targetIP = args.ip or MAC2IPv4(args.mac)
    if args.edt == "":
        edt = "00"
    else:
        nedt = len(args.edt) // 2
        edt = f"{nedt:02d}" + args.edt

    # header: EHD1: ECHONET Lite (10) + EHD2 (81) + Transaction ID
    header = "1081 " + "0001"
    message = " ".join([header, args.seoj, args.deoj,
                       args.esv, "01", args.epc, edt])  # 01 = OPC
    if args.verbose:
        print(f"[info] targetIP={targetIP} message={message}")

    ret = echonet(targetIP, message)
    if ret == "":
        retstr = ""
    else:
        retstr = str(binascii.hexlify(ret), "utf-8")

    if args.verbose:
        retstrinfo = re.sub(
            r"(\w{4})(\w{4})(\w{6})(\w{6})(\w{2})(\w{2})(\w{2})(\w+)", r"\1 \2 \3 \4 \5 \6 \7 \8", retstr)
        print(f"[info] ret={retstrinfo}")
    if args.edc_only:
        ret_edc = retstr[26:]
        if ret_edc == "00":
            pass    # Empty
        else:
            print(convert_edc(ret_edc[2:], args.edc_only))
    else:
        print(retstr)


if __name__ == '__main__':
    main()
