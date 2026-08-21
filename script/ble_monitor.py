#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "bleak",
# ]
# ///
"""
ble_monitor.py -- live BLE advertisement monitor (curses TUI).

Three things on one screen:
  * status : scanner state, packet rate, how many devices are advertising now
  * list   : every advertiser with live RSSI + sparkline (move with arrow keys)
  * detail : full advertisement dump of the selected device, plus an
             RSSI-versus-time chart so you can watch the signal move

Both names are always reported side by side, because they often disagree:
  * ADV NAME -- the Complete/Shortened Local Name inside the advertisement
  * OS NAME  -- what this machine reports for the device (on macOS the
                CoreBluetooth cache, i.e. the name Finder/Settings shows;
                on Linux the BlueZ cache). It can be present with no
                advertised name at all, stale, or renamed by the OS.

Usage:
    ./ble_monitor.py                       # interactive TUI
    ./ble_monitor.py --filter T02          # only names/addresses matching "T02"
    ./ble_monitor.py --csv rssi.csv        # log every packet while monitoring
    ./ble_monitor.py --list --duration 8   # one-shot plain-text table, no TUI

Keys (list view):
    up/down, k/j   move selection        Enter, right   open detail view
    s              cycle sort order      /              edit name filter
    space          freeze the display (scanning keeps running)
    a              show/hide stale devices
    r              reset stats of the selected device
    q              quit (only q quits, so a stray Esc costs nothing)
Keys (detail view):
    +/-            chart time span       left, Esc, q   back to the list
    r              reset stats

macOS: the terminal application needs Bluetooth permission
(System Settings -> Privacy & Security -> Bluetooth).
Linux: --adapter hci1 selects a specific controller.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import curses
import csv
import time
import unicodedata
from collections import deque
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, Sequence

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

try:  # bleak keeps the SIG service-UUID table, but the name moved around
    from bleak.uuids import uuidstr_to_str as _bleak_uuid_name
except ImportError:  # pragma: no cover - depends on bleak version
    _bleak_uuid_name = None


# ------------------------------------------------------------------- constants

RSSI_HISTORY = 4000          # samples kept per device
RSSI_FLOOR = -100            # dBm, bottom of the chart when data is flat
RSSI_CEIL = -30              # dBm, top of the chart when data is flat
RSSI_AT_1M_DEFAULT = -59     # dBm, typical reading one metre from a BLE device
FSPL_AT_1M_DB = 41           # 2.4 GHz free-space loss over the first metre
STALE_AFTER = 10.0           # seconds without a packet -> dimmed
SPARK_SPAN = 30.0            # seconds covered by the list sparkline
SPARK_WIDTH = 16
CHART_SPANS = (15.0, 30.0, 60.0, 120.0, 300.0, 600.0)
DEFAULT_SPAN_INDEX = 2

BLOCKS = " ▁▂▃▄▅▆▇█"        # index 0 = no data
EIGHTHS = "▁▂▃▄▅▆▇█"        # partial top cell of a bar

SORT_MODES = ("rssi", "name", "last", "addr", "packets")

# Bluetooth SIG company identifiers -- partial table, the full list lives in the
# SIG "Assigned Numbers" document. Unknown IDs are shown as raw hex.
COMPANY_IDS: dict[int, str] = {
    0x0000: "Ericsson (often just a placeholder)",
    0x0001: "Nokia Mobile Phones",
    0x0002: "Intel Corp.",
    0x0003: "IBM Corp.",
    0x0006: "Microsoft",
    0x000A: "Cambridge Silicon Radio",
    0x000D: "Texas Instruments",
    0x000F: "Broadcom",
    0x0030: "ST Microelectronics",
    0x004C: "Apple, Inc.",
    0x0059: "Nordic Semiconductor ASA",
    0x0075: "Samsung Electronics",
    0x0087: "Garmin International",
    0x009E: "Bose Corporation",
    0x00C4: "LG Electronics",
    0x00E0: "Google",
    0x0110: "Seiko Epson",
    0x0118: "Sharp Corporation",
    0x012D: "Sony Corporation",
    0x0131: "Cypress Semiconductor",
    0x0154: "Panasonic",
    0x0157: "Anhui Huami (Xiaomi wearables)",
    0x0171: "Amazon.com Services",
    0x01D7: "Qualcomm",
    0x0243: "Nintendo",
    0x02E5: "Espressif Systems",
    0x038F: "Xiaomi Inc.",
    0x0499: "Ruuvi Innovations",
    0x05A7: "Sonos Inc.",
    0x0822: "Adafruit Industries",
}

# Apple "continuity" message types found inside manufacturer data 0x004C.
APPLE_MESSAGE_TYPES: dict[int, str] = {
    0x02: "iBeacon",
    0x03: "AirPrint",
    0x05: "AirDrop",
    0x06: "HomeKit",
    0x07: "Proximity Pairing (AirPods etc.)",
    0x08: "Hey Siri",
    0x09: "AirPlay Target",
    0x0A: "AirPlay Source",
    0x0B: "Magic Switch",
    0x0C: "Handoff",
    0x0D: "Tethering Target",
    0x0E: "Tethering Source",
    0x0F: "Nearby Action",
    0x10: "Nearby Info",
    0x12: "Find My",
}

# Service UUIDs worth naming even when bleak's table misses them.
EXTRA_SERVICE_NAMES: dict[str, str] = {
    "0000fd6f-0000-1000-8000-00805f9b34fb": "Exposure Notification",
    "0000fe2c-0000-1000-8000-00805f9b34fb": "Google Fast Pair",
    "0000feaa-0000-1000-8000-00805f9b34fb": "Eddystone",
    "0000fe9f-0000-1000-8000-00805f9b34fb": "Google",
    "0000fd5a-0000-1000-8000-00805f9b34fb": "Samsung",
    "0000ff00-0000-1000-8000-00805f9b34fb": "vendor-specific (0xFF00)",
}

EDDYSTONE_UUID = "0000feaa-0000-1000-8000-00805f9b34fb"
EDDYSTONE_SCHEMES = ("http://www.", "https://www.", "http://", "https://")
EDDYSTONE_EXPANSIONS = {
    0x00: ".com/", 0x01: ".org/", 0x02: ".edu/", 0x03: ".net/",
    0x04: ".info/", 0x05: ".biz/", 0x06: ".gov/",
    0x07: ".com", 0x08: ".org", 0x09: ".edu", 0x0A: ".net",
    0x0B: ".info", 0x0C: ".biz", 0x0D: ".gov",
}


# --------------------------------------------------------------- text metrics
# Device names arrive from the air and are full Unicode: "カード" is three code
# points but six terminal cells. Every column is measured in cells, never in
# code points, or one Japanese name shifts the whole rest of the row.


def cell_width(char: str) -> int:
    """How many terminal cells one character occupies."""
    if unicodedata.combining(char):
        return 0
    # "W"ide and "F"ullwidth take two cells. "A"mbiguous (box drawing, ★, the
    # sparkline blocks) is one cell in a terminal's default configuration.
    return 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1


def display_width(text: str) -> int:
    return sum(cell_width(char) for char in text)


def truncate_to_cells(text: str, width: int) -> tuple[str, int]:
    """Cut `text` so it fits `width` cells; never splits a wide character."""
    used = 0
    for index, char in enumerate(text):
        char_width = cell_width(char)
        if used + char_width > width:
            return text[:index], used
        used += char_width
    return text, used


def clip(text: str, width: int) -> str:
    return truncate_to_cells(text, max(0, width))[0]


def fit(text: str, width: int, align: str = "<") -> str:
    """Truncate and pad `text` to exactly `width` terminal cells."""
    body, used = truncate_to_cells(text, max(0, width))
    padding = " " * (max(0, width) - used)
    return padding + body if align == ">" else body + padding


def printable(text: str) -> str:
    """Make an over-the-air name safe to draw.

    Control and format characters would corrupt the screen, so they become "·".
    Exotic spaces are kept as spaces instead -- Apple really does put U+00A0
    inside names like "kcrt's Apple Watch", and "Apple·Watch" would be a lie.
    """
    characters = []
    for char in text:
        if unicodedata.category(char) in ("Zs", "Zl", "Zp"):
            characters.append(" ")
        else:
            characters.append(char if char.isprintable() else "·")
    return "".join(characters)


# ------------------------------------------------------------------- utilities


def company_name(company_id: int) -> str:
    return COMPANY_IDS.get(company_id, f"unknown (0x{company_id:04X})")


def service_name(uuid: str) -> str:
    """Human name for a 128-bit service UUID string, or "" when unknown."""
    uuid = uuid.lower()
    if uuid in EXTRA_SERVICE_NAMES:
        return EXTRA_SERVICE_NAMES[uuid]
    if _bleak_uuid_name is not None:
        with contextlib.suppress(Exception):
            name = _bleak_uuid_name(uuid)
            if name and name.lower() != uuid:
                return name
    return ""


def short_uuid(uuid: str) -> str:
    """Collapse a Bluetooth-base UUID down to its 16-bit form."""
    lowered = uuid.lower()
    if lowered.startswith("0000") and lowered.endswith("-0000-1000-8000-00805f9b34fb"):
        return f"0x{lowered[4:8].upper()}"
    return lowered


def hexdump(data: bytes, width: int = 16) -> list[str]:
    """Classic offset / hex / ASCII dump, one string per line."""
    lines: list[str] = []
    for offset in range(0, len(data), width):
        chunk = data[offset : offset + width]
        hexpart = " ".join(f"{b:02x}" for b in chunk).ljust(width * 3 - 1)
        text = "".join(chr(b) if 0x20 <= b < 0x7F else "." for b in chunk)
        lines.append(f"{offset:04x}  {hexpart}  {text}")
    return lines


def reference_rssi_1m(tx_power: int | None) -> int:
    """RSSI to expect one metre away.

    The advertised TX Power Level is the power at the antenna, not the RSSI at
    1 m, so subtract the 2.4 GHz free-space loss over that first metre. Without
    an advertised value, fall back to the usual measured ballpark.
    """
    return tx_power - FSPL_AT_1M_DB if tx_power is not None else RSSI_AT_1M_DEFAULT


def estimate_distance_m(rssi: float, rssi_at_1m: int = RSSI_AT_1M_DEFAULT,
                        path_loss: float = 2.0) -> float:
    """Log-distance path-loss estimate. Indoors this is a guess, not a measurement."""
    return 10.0 ** ((rssi_at_1m - rssi) / (10.0 * path_loss))


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def is_valid_rssi(rssi: int | None) -> bool:
    """Some stacks report 127 (or a positive value) when they have no reading."""
    return rssi is not None and -127 < rssi < 0


# ----------------------------------------------------- advertisement decoding


def decode_ibeacon(payload: bytes) -> list[str]:
    """Apple type 0x02 -- iBeacon: 16-byte proximity UUID, major, minor, power."""
    if len(payload) < 23 or payload[0] != 0x02:
        return []
    body = payload[2:]
    raw_uuid = body[0:16].hex()
    uuid = "-".join(
        (raw_uuid[0:8], raw_uuid[8:12], raw_uuid[12:16], raw_uuid[16:20], raw_uuid[20:32])
    )
    major = int.from_bytes(body[16:18], "big")
    minor = int.from_bytes(body[18:20], "big")
    tx_power = int.from_bytes(body[20:21], "big", signed=True)
    return [
        f"iBeacon UUID   {uuid}",
        f"major / minor  {major} / {minor}",
        f"ref. TX power  {tx_power} dBm at 1 m",
    ]


def decode_apple(payload: bytes) -> list[str]:
    """Walk the type/length/value chain Apple packs into 0x004C."""
    lines = decode_ibeacon(payload)
    if lines:
        return lines
    offset = 0
    while offset + 1 < len(payload):
        msg_type = payload[offset]
        length = payload[offset + 1]
        value = payload[offset + 2 : offset + 2 + length]
        name = APPLE_MESSAGE_TYPES.get(msg_type, f"type 0x{msg_type:02X}")
        lines.append(f"{name}: {value.hex(' ') or '(empty)'}")
        offset += 2 + length
    return lines


def decode_eddystone(payload: bytes) -> list[str]:
    """Eddystone UID / URL / TLM / EID frames."""
    if not payload:
        return []
    frame = payload[0]
    if frame == 0x00 and len(payload) >= 18:
        return [
            "Eddystone-UID",
            f"namespace  {payload[2:12].hex()}",
            f"instance   {payload[12:18].hex()}",
            f"ranging    {int.from_bytes(payload[1:2], 'big', signed=True)} dBm at 0 m",
        ]
    if frame == 0x10 and len(payload) >= 3:
        scheme = EDDYSTONE_SCHEMES[payload[2]] if payload[2] < len(EDDYSTONE_SCHEMES) else "?"
        url = scheme + "".join(
            EDDYSTONE_EXPANSIONS.get(b, chr(b) if 0x20 <= b < 0x7F else ".")
            for b in payload[3:]
        )
        return ["Eddystone-URL", f"url  {url}"]
    if frame == 0x20 and len(payload) >= 14:
        voltage = int.from_bytes(payload[2:4], "big")
        temp_raw = int.from_bytes(payload[4:6], "big", signed=True)
        return [
            "Eddystone-TLM",
            f"battery    {voltage} mV",
            f"temperature{temp_raw / 256.0:8.1f} degC",
            f"adv count  {int.from_bytes(payload[6:10], 'big')}",
            f"uptime     {int.from_bytes(payload[10:14], 'big') / 10.0:.0f} s",
        ]
    if frame == 0x30:
        return ["Eddystone-EID", f"ephemeral id  {payload[2:].hex()}"]
    return []


def decode_ruuvi(payload: bytes) -> list[str]:
    """RuuviTag data format 5 -- a common sensor beacon worth reading directly."""
    if len(payload) < 24 or payload[0] != 0x05:
        return []
    temp = int.from_bytes(payload[1:3], "big", signed=True) * 0.005
    humidity = int.from_bytes(payload[3:5], "big") * 0.0025
    pressure = int.from_bytes(payload[5:7], "big") + 50000
    power = int.from_bytes(payload[13:15], "big")
    return [
        "RuuviTag format 5",
        f"temperature {temp:.2f} degC",
        f"humidity    {humidity:.2f} %",
        f"pressure    {pressure / 100.0:.2f} hPa",
        f"battery     {(power >> 5) + 1600} mV",
    ]


def decode_manufacturer(company_id: int, payload: bytes) -> list[str]:
    if company_id == 0x004C:
        return decode_apple(payload)
    if company_id == 0x0499:
        return decode_ruuvi(payload)
    if company_id == 0x0006 and payload[:1] == b"\x03":
        return ["Microsoft Swift Pair"]
    return []


def decode_service_payload(uuid: str, payload: bytes) -> list[str]:
    if uuid.lower() == EDDYSTONE_UUID:
        return decode_eddystone(payload)
    return []


# ----------------------------------------------------------------- data model


@dataclass(slots=True)
class Sample:
    t: float          # time.monotonic()
    rssi: int


@dataclass
class DeviceRecord:
    """Everything seen from one advertiser, plus its RSSI history."""

    address: str
    first_seen: float
    last_seen: float
    adv_name: str | None = None      # Local Name field of the advertisement
    os_name: str | None = None       # what CoreBluetooth / BlueZ reports
    packets: int = 0
    invalid_rssi: int = 0            # packets whose RSSI the stack did not report
    tx_power: int | None = None
    manufacturer_data: dict[int, bytes] = field(default_factory=dict)
    service_data: dict[str, bytes] = field(default_factory=dict)
    service_uuids: list[str] = field(default_factory=list)
    samples: deque[Sample] = field(default_factory=lambda: deque(maxlen=RSSI_HISTORY))

    # -- updates ------------------------------------------------------------

    def update(self, now: float, device: BLEDevice, adv: AdvertisementData) -> None:
        self.last_seen = now
        self.packets += 1
        if is_valid_rssi(adv.rssi):
            self.samples.append(Sample(now, adv.rssi))
        else:
            self.invalid_rssi += 1
        # Keep the two name sources apart: they disagree often enough to matter.
        if adv.local_name:
            self.adv_name = printable(adv.local_name)
        if device.name:
            self.os_name = printable(device.name)
        if adv.tx_power is not None:
            self.tx_power = adv.tx_power
        if adv.manufacturer_data:
            self.manufacturer_data.update(adv.manufacturer_data)
        if adv.service_data:
            self.service_data.update(adv.service_data)
        for uuid in adv.service_uuids:
            if uuid not in self.service_uuids:
                self.service_uuids.append(uuid)

    def reset_stats(self, now: float) -> None:
        last = self.samples[-1] if self.samples else None
        self.samples.clear()
        if last is not None:
            self.samples.append(Sample(now, last.rssi))
        self.packets = 1 if last is not None else 0
        self.invalid_rssi = 0
        self.first_seen = now

    # -- derived values -----------------------------------------------------

    @property
    def display_name(self) -> str:
        """Best single label: the advertised name wins, the OS name backs it up."""
        return self.adv_name or self.os_name or "(no name)"

    @property
    def names_differ(self) -> bool:
        return bool(self.adv_name and self.os_name and self.adv_name != self.os_name)

    @property
    def rssi(self) -> int | None:
        return self.samples[-1].rssi if self.samples else None

    def window(self, now: float, span: float) -> list[Sample]:
        return [s for s in self.samples if now - s.t <= span]

    def stats(self, samples: Sequence[Sample] | None = None) -> tuple[int, int, float] | None:
        """(min, max, mean) over the given samples, or over all of them."""
        pool = list(self.samples if samples is None else samples)
        if not pool:
            return None
        values = [s.rssi for s in pool]
        return min(values), max(values), sum(values) / len(values)

    def packet_rate(self, now: float, span: float = 10.0) -> float:
        recent = self.window(now, span)
        if len(recent) < 2:
            return 0.0
        elapsed = max(now, recent[-1].t) - recent[0].t
        return len(recent) / elapsed if elapsed > 0 else 0.0

    def age(self, now: float) -> float:
        return now - self.last_seen

    def is_stale(self, now: float) -> bool:
        return self.age(now) > STALE_AFTER

    def matches(self, needle: str) -> bool:
        if not needle:
            return True
        needle = needle.lower()
        haystack = (self.address, self.adv_name or "", self.os_name or "")
        return any(needle in field.lower() for field in haystack)


class Monitor:
    """Collects advertisements; owns no UI."""

    def __init__(self, csv_path: Path | None = None, forget_after: float = 0.0) -> None:
        self.devices: dict[str, DeviceRecord] = {}
        self.packets = 0
        self.started = time.monotonic()
        self.forget_after = forget_after
        self._csv_file = None
        self._csv_writer = None
        if csv_path is not None:
            self._csv_file = csv_path.open("a", newline="", encoding="utf-8")
            self._csv_writer = csv.writer(self._csv_file)
            if csv_path.stat().st_size == 0:
                self._csv_writer.writerow(
                    ["iso_time", "address", "adv_name", "os_name", "rssi"]
                )

    # -- bleak callback -----------------------------------------------------

    def on_detection(self, device: BLEDevice, adv: AdvertisementData) -> None:
        now = time.monotonic()
        self.packets += 1
        record = self.devices.get(device.address)
        if record is None:
            record = DeviceRecord(address=device.address, first_seen=now, last_seen=now)
            self.devices[device.address] = record
        record.update(now, device, adv)
        if self._csv_writer is not None:
            self._csv_writer.writerow(
                [datetime.now().isoformat(timespec="milliseconds"), device.address,
                 record.adv_name or "", record.os_name or "",
                 adv.rssi if is_valid_rssi(adv.rssi) else ""]
            )

    # -- housekeeping -------------------------------------------------------

    def prune(self, now: float) -> None:
        if self.forget_after <= 0:
            return
        for address in [a for a, d in self.devices.items()
                        if d.age(now) > self.forget_after]:
            del self.devices[address]

    def flush(self) -> None:
        if self._csv_file is not None:
            self._csv_file.flush()

    def close(self) -> None:
        if self._csv_file is not None:
            self._csv_file.close()
            self._csv_file = None

    def sorted_devices(self, mode: str, needle: str, show_stale: bool,
                       now: float) -> list[DeviceRecord]:
        pool = [d for d in self.devices.values() if d.matches(needle)]
        if not show_stale:
            pool = [d for d in pool if not d.is_stale(now)]
        keys = {
            "rssi": lambda d: (-(d.rssi if d.rssi is not None else -999), d.address),
            "name": lambda d: (d.adv_name is None and d.os_name is None,
                               d.display_name.lower(), d.address),
            "last": lambda d: (d.age(now), d.address),
            "addr": lambda d: d.address,
            "packets": lambda d: (-d.packets, d.address),
        }
        return sorted(pool, key=keys[mode])

    def elapsed(self, now: float) -> float:
        return now - self.started

    def packet_rate(self, now: float) -> float:
        elapsed = self.elapsed(now)
        return self.packets / elapsed if elapsed > 0 else 0.0


# --------------------------------------------------------------- chart drawing


def bucket_samples(samples: Iterable[Sample], width: int, span: float,
                   now: float) -> list[float | None]:
    """Average the samples into `width` time buckets; None where nothing came in."""
    if width <= 0:
        return []
    buckets: list[list[int]] = [[] for _ in range(width)]
    bucket_span = span / width
    for sample in samples:
        age = now - sample.t
        if age < 0 or age > span:
            continue
        index = width - 1 - int(age / bucket_span)
        if 0 <= index < width:
            buckets[index].append(sample.rssi)
    return [sum(b) / len(b) if b else None for b in buckets]


def chart_scale(values: Sequence[float | None]) -> tuple[float, float]:
    """Pick a y-range that contains the data with a little breathing room."""
    present = [v for v in values if v is not None]
    if not present:
        return float(RSSI_FLOOR), float(RSSI_CEIL)
    low, high = min(present), max(present)
    if high - low < 10:                      # keep flat traces from filling the box
        middle = (high + low) / 2
        low, high = middle - 5, middle + 5
    margin = (high - low) * 0.15
    return max(RSSI_FLOOR, low - margin), min(0.0, high + margin)


def render_bars(values: Sequence[float | None], height: int,
                low: float, high: float) -> list[str]:
    """Bar chart as `height` strings, topmost row first."""
    rows = [[" "] * len(values) for _ in range(height)]
    span = high - low or 1.0
    for column, value in enumerate(values):
        if value is None:
            continue
        eighths = round(clamp((value - low) / span, 0.0, 1.0) * height * 8)
        eighths = max(1, eighths)            # a present sample always shows something
        full, remainder = divmod(eighths, 8)
        for row in range(min(full, height)):
            rows[height - 1 - row][column] = "█"
        if remainder and full < height:
            rows[height - 1 - full][column] = EIGHTHS[remainder - 1]
    return ["".join(row) for row in rows]


def sparkline(samples: Sequence[Sample], width: int, span: float, now: float) -> str:
    values = bucket_samples(samples, width, span, now)
    low, high = chart_scale(values)
    scale = (high - low) or 1.0
    out = []
    for value in values:
        if value is None:
            out.append(" ")
        else:
            level = int(clamp((value - low) / scale, 0.0, 1.0) * (len(BLOCKS) - 2))
            out.append(BLOCKS[level + 1])
    return "".join(out)


# ------------------------------------------------------------------ curses UI

# colour pair ids
CP_HEADER, CP_STRONG, CP_OK, CP_WEAK, CP_BAD, CP_DIM, CP_SEL, CP_LABEL = range(1, 9)


def init_colors() -> None:
    with contextlib.suppress(curses.error):
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(CP_HEADER, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(CP_STRONG, curses.COLOR_GREEN, -1)
        curses.init_pair(CP_OK, curses.COLOR_CYAN, -1)
        curses.init_pair(CP_WEAK, curses.COLOR_YELLOW, -1)
        curses.init_pair(CP_BAD, curses.COLOR_RED, -1)
        curses.init_pair(CP_DIM, curses.COLOR_WHITE, -1)
        curses.init_pair(CP_SEL, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(CP_LABEL, curses.COLOR_MAGENTA, -1)


Stats = tuple[int, int, float] | None


@dataclass(frozen=True)
class Column:
    """One column of the device list. `priority` 0 is never dropped."""

    header: str
    width: int
    priority: int
    render: Callable[[DeviceRecord, float, Stats], str]
    align: str = "<"


LIST_COLUMNS: tuple[Column, ...] = (
    Column("ADDRESS", 38, 0, lambda d, t, s: d.address),
    Column("ADV NAME", 20, 0, lambda d, t, s: d.adv_name or "-"),
    Column("OS NAME", 20, 0, lambda d, t, s: d.os_name or "-"),
    Column("RSSI", 5, 0, lambda d, t, s: "-" if d.rssi is None else str(d.rssi), ">"),
    Column("AGE", 6, 1, lambda d, t, s: f"{d.age(t):.1f}s", ">"),
    Column(f"RSSI -{SPARK_SPAN:.0f}s..now", SPARK_WIDTH, 2,
           lambda d, t, s: sparkline(d.samples, SPARK_WIDTH, SPARK_SPAN, t)),
    Column("AVG", 6, 3, lambda d, t, s: f"{s[2]:.1f}" if s else "-", ">"),
    Column("PKT", 6, 4, lambda d, t, s: str(d.packets), ">"),
    Column("MIN", 5, 5, lambda d, t, s: str(s[0]) if s else "-", ">"),
    Column("MAX", 5, 5, lambda d, t, s: str(s[1]) if s else "-", ">"),
)


#: Text columns that may be squeezed on a narrow terminal, and how far.
SHRINKABLE: dict[str, int] = {"ADDRESS": 8, "ADV NAME": 6, "OS NAME": 6}


def layout_columns(total_width: int, address_width: int) -> list[Column]:
    """Fit the list columns into the terminal.

    First drop the least useful columns (highest priority number), then squeeze
    the text columns. The two name columns are never dropped -- seeing both the
    advertised and the OS name side by side is the point of the list.
    """
    columns = [replace(c, width=address_width) if c.header == "ADDRESS" else c
               for c in LIST_COLUMNS]
    used = lambda cols: sum(c.width for c in cols) + len(cols) - 1  # noqa: E731

    while used(columns) > total_width and any(c.priority for c in columns):
        columns.remove(max(enumerate(columns), key=lambda p: (p[1].priority, p[0]))[1])

    while used(columns) > total_width:
        squeezable = [(index, column) for index, column in enumerate(columns)
                      if column.width > SHRINKABLE.get(column.header, column.width)]
        if not squeezable:
            break
        index, column = max(squeezable, key=lambda pair: pair[1].width)
        columns[index] = replace(column, width=column.width - 1)
    return columns


def format_row(columns: Sequence[Column], device: DeviceRecord, as_of: float,
               stats: Stats) -> str:
    return " ".join(fit(c.render(device, as_of, stats), c.width, c.align) for c in columns)


def format_header(columns: Sequence[Column]) -> str:
    return " ".join(fit(c.header, c.width, c.align) for c in columns)


#: Final bytes of CSI/SS3 sequences, and the key codes they stand for.
ESCAPE_FINALS: dict[str, int] = {
    "A": curses.KEY_UP, "B": curses.KEY_DOWN, "C": curses.KEY_RIGHT,
    "D": curses.KEY_LEFT, "H": curses.KEY_HOME, "F": curses.KEY_END,
}
#: CSI "<number>~" sequences.
ESCAPE_TILDE: dict[int, int] = {
    1: curses.KEY_HOME, 4: curses.KEY_END,
    5: curses.KEY_PPAGE, 6: curses.KEY_NPAGE,
}


def read_keys(stdscr: "curses.window") -> list[int]:
    """Drain pending input into key codes.

    Terminals disagree about application-keypad mode: an arrow key arrives as
    ESC O B or as ESC [ B, and terminfo only folds one of the two into
    KEY_DOWN. Translate the leftovers here so the arrows work either way and a
    stray escape sequence is swallowed instead of being read as a bare Esc.
    """
    raw: list[int] = []
    while (key := stdscr.getch()) != -1:
        raw.append(key)

    keys: list[int] = []
    index = 0
    while index < len(raw):
        key = raw[index]
        if key != 27 or index + 1 >= len(raw):
            keys.append(key)
            index += 1
            continue
        if raw[index + 1] not in (ord("["), ord("O")):
            keys.append(27)               # a real Esc that happens to precede typing
            index += 1
            continue
        cursor = index + 2
        digits = ""
        while cursor < len(raw) and chr(raw[cursor]).isdigit():
            digits += chr(raw[cursor])
            cursor += 1
        if cursor < len(raw):
            final = chr(raw[cursor])
            if final in ESCAPE_FINALS:
                keys.append(ESCAPE_FINALS[final])
            elif final == "~" and digits:
                if (mapped := ESCAPE_TILDE.get(int(digits))) is not None:
                    keys.append(mapped)
            cursor += 1
        index = cursor
    return keys


def rssi_attr(rssi: int | None) -> int:
    if rssi is None:
        return curses.color_pair(CP_DIM) | curses.A_DIM
    if rssi >= -60:
        return curses.color_pair(CP_STRONG)
    if rssi >= -75:
        return curses.color_pair(CP_OK)
    if rssi >= -90:
        return curses.color_pair(CP_WEAK)
    return curses.color_pair(CP_BAD)


class Screen:
    """Thin wrapper that clips writes so a small terminal never raises."""

    def __init__(self, stdscr: "curses.window") -> None:
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()

    def refresh_size(self) -> None:
        self.height, self.width = self.stdscr.getmaxyx()

    def put(self, y: int, x: int, text: str, attr: int = 0) -> None:
        if not (0 <= y < self.height) or x >= self.width:
            return
        room = self.width - x
        if y == self.height - 1:
            room -= 1                        # writing the last cell scrolls
        if room <= 0:
            return
        with contextlib.suppress(curses.error):
            self.stdscr.addstr(y, x, clip(text, room), attr)

    def bar(self, y: int, text: str, attr: int) -> None:
        """Fill a whole row, so the highlight reaches the right edge."""
        self.put(y, 0, fit(text, self.width - (y == self.height - 1)), attr)


class UI:
    """List view + detail view over a Monitor."""

    def __init__(self, screen: Screen, monitor: Monitor, needle: str = "") -> None:
        self.screen = screen
        self.monitor = monitor
        self.needle = needle
        self.sort_index = 0
        self.show_stale = True
        self.paused = False
        self.selected: str | None = None
        self.scroll = 0
        self.detail: str | None = None       # address being inspected
        self.span_index = DEFAULT_SPAN_INDEX
        self.editing_filter = False
        self.filter_buffer = ""
        self.status = ""
        self.frozen: list[DeviceRecord] = []
        self.frozen_at = 0.0

    # -- state --------------------------------------------------------------

    @property
    def sort_mode(self) -> str:
        return SORT_MODES[self.sort_index]

    @property
    def span(self) -> float:
        return CHART_SPANS[self.span_index]

    def visible(self, now: float) -> tuple[list[DeviceRecord], float]:
        """Device list to draw; while paused the previous snapshot is reused."""
        if self.paused and self.frozen:
            return self.frozen, self.frozen_at
        devices = self.monitor.sorted_devices(self.sort_mode, self.needle,
                                              self.show_stale, now)
        self.frozen, self.frozen_at = devices, now
        return devices, now

    def record(self, address: str | None) -> DeviceRecord | None:
        return self.monitor.devices.get(address) if address else None

    # -- input --------------------------------------------------------------

    def handle_key(self, key: int, devices: list[DeviceRecord], now: float) -> bool:
        """Return False to quit."""
        if self.editing_filter:
            self._edit_filter(key)
            return True

        if key == 27:                         # Esc steps back; it never quits
            self.detail = None
            return True
        if key == ord("q"):
            if self.detail is not None:
                self.detail = None
                return True
            return False
        if key == ord("/"):
            self.editing_filter = True
            self.filter_buffer = self.needle
            return True
        if key == ord("s"):
            self.sort_index = (self.sort_index + 1) % len(SORT_MODES)
            self.status = f"sort: {self.sort_mode}"
        elif key == ord(" "):
            self.paused = not self.paused
            self.status = "display frozen (scan continues)" if self.paused else "resumed"
        elif key == ord("a"):
            self.show_stale = not self.show_stale
            self.status = f"stale devices: {'shown' if self.show_stale else 'hidden'}"
        elif key == ord("r"):
            target = self.record(self.detail or self.selected)
            if target is not None:
                target.reset_stats(now)
                self.status = f"stats reset for {target.address}"
        elif key in (ord("+"), ord("=")):
            self.span_index = min(self.span_index + 1, len(CHART_SPANS) - 1)
        elif key in (ord("-"), ord("_")):
            self.span_index = max(self.span_index - 1, 0)
        elif self.detail is None:
            self._handle_list_key(key, devices)
        elif key in (curses.KEY_LEFT, ord("h")):
            self.detail = None
        return True

    def _handle_list_key(self, key: int, devices: list[DeviceRecord]) -> None:
        if not devices:
            return
        addresses = [d.address for d in devices]
        index = addresses.index(self.selected) if self.selected in addresses else 0
        if key in (curses.KEY_DOWN, ord("j")):
            index += 1
        elif key in (curses.KEY_UP, ord("k")):
            index -= 1
        elif key == curses.KEY_NPAGE:
            index += 10
        elif key == curses.KEY_PPAGE:
            index -= 10
        elif key == curses.KEY_HOME:
            index = 0
        elif key == curses.KEY_END:
            index = len(addresses) - 1
        elif key in (curses.KEY_RIGHT, curses.KEY_ENTER, 10, 13, ord("l")):
            self.detail = self.selected or addresses[0]
            return
        else:
            return
        self.selected = addresses[int(clamp(index, 0, len(addresses) - 1))]

    def _edit_filter(self, key: int) -> None:
        if key in (curses.KEY_ENTER, 10, 13):
            self.needle = self.filter_buffer
            self.editing_filter = False
            self.status = f"filter: {self.needle or '(none)'}"
        elif key == 27:                      # Esc -> cancel
            self.editing_filter = False
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            self.filter_buffer = self.filter_buffer[:-1]
        elif 32 <= key < 127:
            self.filter_buffer += chr(key)

    # -- drawing ------------------------------------------------------------

    def draw(self, now: float, scanning: bool) -> None:
        self.screen.refresh_size()
        self.screen.stdscr.erase()
        devices, as_of = self.visible(now)
        if self.selected not in {d.address for d in devices}:
            self.selected = devices[0].address if devices else None

        self._draw_header(now, scanning, len(devices))
        if self.detail is not None and self.record(self.detail) is not None:
            self._draw_detail(self.record(self.detail), now)
        else:
            self.detail = None
            self._draw_list(devices, as_of)
        self._draw_footer()
        self.screen.stdscr.refresh()

    def _draw_header(self, now: float, scanning: bool, shown: int) -> None:
        state = "SCANNING" if scanning else "STOPPED "
        if self.paused:
            state = "FROZEN  "
        left = (f" BLE monitor  [{state}]  {self.monitor.elapsed(now):6.0f}s"
                f"  devices {len(self.monitor.devices):3d} (shown {shown:3d})"
                f"  packets {self.monitor.packets:6d} ({self.monitor.packet_rate(now):5.1f}/s)")
        right = f"sort {self.sort_mode}  span {self.span:.0f}s  filter {self.needle or '-'} "
        pad = max(1, self.screen.width - display_width(left) - display_width(right))
        self.screen.bar(0, left + " " * pad + right, curses.color_pair(CP_HEADER) | curses.A_BOLD)

    def _draw_list(self, devices: list[DeviceRecord], as_of: float) -> None:
        # Addresses are 17 chars on Linux but 36-char UUIDs on macOS: only pay
        # for the width the current backend actually needs.
        address_width = min(38, max((len(d.address) for d in devices), default=17))
        columns = layout_columns(self.screen.width - 1, address_width)
        self.screen.put(1, 0, format_header(columns), curses.A_BOLD | curses.A_UNDERLINE)

        rows = max(1, self.screen.height - 4)
        addresses = [d.address for d in devices]
        cursor = addresses.index(self.selected) if self.selected in addresses else 0
        self.scroll = int(clamp(self.scroll, max(0, cursor - rows + 1), max(0, cursor)))
        self.scroll = min(self.scroll, max(0, len(devices) - rows))

        for line, device in enumerate(devices[self.scroll : self.scroll + rows]):
            stats = device.stats(device.window(as_of, SPARK_SPAN))
            text = format_row(columns, device, as_of, stats)
            attr = rssi_attr(device.rssi)
            if device.is_stale(as_of):
                attr = curses.color_pair(CP_DIM) | curses.A_DIM
            if device.address == self.selected:
                attr = curses.color_pair(CP_SEL) | curses.A_BOLD
            self.screen.put(2 + line, 0, fit(text, self.screen.width - 1), attr)

        if not devices:
            self.screen.put(3, 2, "waiting for advertisements...",
                            curses.color_pair(CP_DIM) | curses.A_DIM)

    def _draw_detail(self, device: DeviceRecord, now: float) -> None:
        left_width = min(52, max(30, self.screen.width // 2 - 2))
        body_top, body_bottom = 1, self.screen.height - 3

        for row, (label, value) in enumerate(self._detail_fields(device, now)):
            y = body_top + row
            if y > body_bottom:
                break
            if label == "":                  # section heading
                self.screen.put(y, 0, clip(value, left_width),
                                curses.color_pair(CP_LABEL) | curses.A_BOLD)
                continue
            self.screen.put(y, 0, fit(label, 14), curses.A_DIM)
            attr = rssi_attr(device.rssi) if label.startswith("RSSI") else 0
            self.screen.put(y, 15, clip(value, left_width - 15), attr)

        chart_left = left_width + 2
        chart_width = self.screen.width - chart_left - 1
        if chart_width >= 24:
            self._draw_chart(device, now, body_top, body_bottom, chart_left, chart_width)

    def _detail_fields(self, device: DeviceRecord, now: float) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = [("", "-- device --")]
        rssi = device.rssi
        window = device.window(now, self.span)
        rows += [
            ("address", device.address),
            ("adv name", device.adv_name or "(not advertised)"),
            ("OS name", device.os_name or "(not known to this Mac)"),
        ]
        if device.names_differ:
            rows.append(("", "  ! advertised name and OS name disagree"))
        rows.append(("RSSI now", f"{rssi} dBm" if rssi is not None
                     else "n/a (not reported by this stack)"))
        overall = device.stats()
        recent = device.stats(window)
        if overall:
            rows.append(("RSSI all", f"min {overall[0]}  max {overall[1]}  avg {overall[2]:.1f}"))
        if recent:
            rows.append((f"RSSI {self.span:.0f}s",
                         f"min {recent[0]}  max {recent[1]}  avg {recent[2]:.1f}"))
        if recent:
            # Averaging first: a single RSSI reading swings several dB packet to packet.
            reference = reference_rssi_1m(device.tx_power)
            rows.append(("distance", f"~{estimate_distance_m(recent[2], reference):.1f} m"
                                     f"  (rough, 1 m ref {reference})"))
        rows += [
            ("packets", f"{device.packets}  ({device.packet_rate(now):.1f}/s)"
                        + (f"  [{device.invalid_rssi} without RSSI]"
                           if device.invalid_rssi else "")),
            ("tracked for", f"{now - device.first_seen:.0f}s"),
            ("last packet", f"{device.age(now):.1f}s ago"),
        ]
        if device.tx_power is not None:
            rows.append(("TX power", f"{device.tx_power} dBm"))

        if device.service_uuids:
            rows.append(("", "-- service UUIDs --"))
            for uuid in device.service_uuids:
                rows.append((short_uuid(uuid), service_name(uuid) or uuid))

        if device.manufacturer_data:
            rows.append(("", "-- manufacturer data --"))
            for company_id, payload in device.manufacturer_data.items():
                rows.append((f"0x{company_id:04X}", company_name(company_id)))
                for line in decode_manufacturer(company_id, payload):
                    rows.append(("", "  " + line))
                for line in hexdump(payload):
                    rows.append(("", "  " + line))

        if device.service_data:
            rows.append(("", "-- service data --"))
            for uuid, payload in device.service_data.items():
                rows.append((short_uuid(uuid), service_name(uuid) or uuid))
                for line in decode_service_payload(uuid, payload):
                    rows.append(("", "  " + line))
                for line in hexdump(payload):
                    rows.append(("", "  " + line))
        return rows

    def _draw_chart(self, device: DeviceRecord, now: float, top: int, bottom: int,
                    left: int, width: int) -> None:
        self.screen.put(top, left,
                        f"RSSI over the last {self.span:.0f}s  (+/- to change span)",
                        curses.color_pair(CP_LABEL) | curses.A_BOLD)
        axis_width = 8
        plot_left = left + axis_width
        plot_width = width - axis_width
        plot_top = top + 2
        plot_height = max(3, bottom - plot_top - 1)

        values = bucket_samples(device.samples, plot_width, self.span, now)
        low, high = chart_scale(values)
        rows = render_bars(values, plot_height, low, high)

        for index, row in enumerate(rows):
            y = plot_top + index
            fraction = 1.0 - (index + 0.5) / plot_height
            label = f"{low + fraction * (high - low):6.0f} "
            self.screen.put(y, left, label, curses.A_DIM)
            self.screen.put(y, plot_left, row, rssi_attr(device.rssi))

        axis_y = plot_top + plot_height
        self.screen.put(axis_y, plot_left, "-" * plot_width, curses.A_DIM)
        span_label = f"-{self.span:.0f}s"
        self.screen.put(axis_y + 1, plot_left, span_label, curses.A_DIM)
        self.screen.put(axis_y + 1, plot_left + plot_width - 3, "now", curses.A_DIM)
        self.screen.put(axis_y + 1, left, "   dBm", curses.A_DIM)

    def _draw_footer(self) -> None:
        y = self.screen.height - 1
        if self.editing_filter:
            self.screen.bar(y, f" filter: {self.filter_buffer}_  (Enter to apply, Esc to cancel)",
                            curses.color_pair(CP_HEADER))
            return
        if self.detail is not None:
            keys = " left/q back   +/- span   r reset stats   space freeze"
        else:
            keys = (" up/down select   Enter detail   s sort   / filter   "
                    "a stale   space freeze   r reset   q quit")
        if self.status:
            keys = f"{keys}   |  {self.status}"
        self.screen.bar(y, keys, curses.color_pair(CP_HEADER))


# ------------------------------------------------------------------ run loops


def scanner_kwargs(args: argparse.Namespace) -> dict:
    kwargs: dict = {"scanning_mode": "passive" if args.passive else "active"}
    if args.adapter:
        kwargs["adapter"] = args.adapter
    return kwargs


async def run_tui(stdscr: "curses.window", args: argparse.Namespace,
                  monitor: Monitor) -> None:
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)
    init_colors()

    ui = UI(Screen(stdscr), monitor, needle=args.filter)
    scanner = BleakScanner(detection_callback=monitor.on_detection, **scanner_kwargs(args))
    interval = 1.0 / args.fps

    await scanner.start()
    try:
        while True:
            now = time.monotonic()
            monitor.prune(now)
            devices, _ = ui.visible(now)
            for key in read_keys(stdscr):
                if not ui.handle_key(key, devices, now):
                    return
            ui.draw(time.monotonic(), scanning=True)
            monitor.flush()
            await asyncio.sleep(interval)
    finally:
        with contextlib.suppress(Exception):
            await scanner.stop()


async def run_list(args: argparse.Namespace, monitor: Monitor) -> None:
    """One-shot plain-text table -- handy for scripts and for logging to CSV."""
    scanner = BleakScanner(detection_callback=monitor.on_detection, **scanner_kwargs(args))
    print(f"scanning for {args.duration:.0f}s ...")
    await scanner.start()
    try:
        await asyncio.sleep(args.duration)
    finally:
        with contextlib.suppress(Exception):
            await scanner.stop()

    now = time.monotonic()
    devices = monitor.sorted_devices("rssi", args.filter, True, now)
    print(f"{fit('ADDRESS', 38)} {fit('ADV NAME', 20)} {fit('OS NAME', 20)} "
          f"{'RSSI':>5} {'AVG':>6} {'MIN':>5} {'MAX':>5} {'PKT':>5}  COMPANY")
    for device in devices:
        stats = device.stats()
        numbers = (f"{stats[2]:>6.1f} {stats[0]:>5d} {stats[1]:>5d}" if stats
                   else f"{'-':>6} {'-':>5} {'-':>5}")
        companies = ", ".join(company_name(c) for c in device.manufacturer_data) or "-"
        print(f"{fit(device.address, 38)} {fit(device.adv_name or '-', 20)} "
              f"{fit(device.os_name or '-', 20)} "
              f"{device.rssi if device.rssi is not None else '-':>5} {numbers} "
              f"{device.packets:>5d}  {companies}")
    print(f"\n{len(devices)} device(s), {monitor.packets} advertisement(s) "
          f"in {monitor.elapsed(now):.1f}s")


# ----------------------------------------------------------------------- main


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Live BLE advertisement monitor: status, device detail, RSSI over time.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("-f", "--filter", default="",
                        help="only show devices whose name or address contains this")
    parser.add_argument("-c", "--csv", type=Path,
                        help="append every advertisement to this CSV file")
    parser.add_argument("--forget", type=float, default=0.0, metavar="SEC",
                        help="drop devices unseen for SEC seconds (0 = keep forever)")
    parser.add_argument("--fps", type=float, default=5.0,
                        help="screen refreshes per second (default: 5)")
    parser.add_argument("--adapter", help="Bluetooth adapter, e.g. hci1 (Linux)")
    parser.add_argument("--passive", action="store_true",
                        help="passive scanning (no scan requests; Linux/BlueZ only)")
    parser.add_argument("-l", "--list", action="store_true",
                        help="one-shot plain-text table instead of the TUI")
    parser.add_argument("-d", "--duration", type=float, default=8.0,
                        help="scan seconds for --list (default: 8)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.csv is not None:
        args.csv.touch(exist_ok=True)
    monitor = Monitor(csv_path=args.csv, forget_after=args.forget)
    try:
        if args.list:
            asyncio.run(run_list(args, monitor))
        else:
            curses.wrapper(lambda stdscr: asyncio.run(run_tui(stdscr, args, monitor)))
    except KeyboardInterrupt:
        pass
    except Exception as exc:                 # noqa: BLE001 - report, do not traceback
        print(f"error: {exc}")
        if args.passive:
            print("hint: passive scanning is BlueZ-only; drop --passive on macOS.")
        print("hint: macOS needs Bluetooth permission for your terminal "
              "(System Settings -> Privacy & Security -> Bluetooth).")
        return 1
    finally:
        monitor.close()
    if args.csv is not None:
        print(f"CSV log: {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
