#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "bleak",
#     "pillow",
# ]
# ///
"""
Phomemo T02 (BLE) minimal driver.

Usage:
    ./phomemo_t02.py image path/to/picture.png
    ./phomemo_t02.py text  "印字したい文字列"
    ./phomemo_t02.py image logo.png --width=30mm
    ./phomemo_t02.py scan

引数を省略するか "-" を渡すと stdin から読む:
    fortune | ./phomemo_t02.py text

詳細は --help / --debug を参照。
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import io
import re
import sys
from collections.abc import AsyncIterator, Callable
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

# ---------------------------------------------------------------- BLE / device

DEVICE_NAME_PREFIX = "T02"
CHAR_WRITE = "0000ff02-0000-1000-8000-00805f9b34fb"
CHAR_NOTIFY = "0000ff03-0000-1000-8000-00805f9b34fb"

WIDTH_DOTS = 384
BYTES_PER_LINE = WIDTH_DOTS // 8  # 48
MAX_LINES_PER_BLOCK = 255

DOTS_PER_MM = 8  # 203dpi。384 dots = 48mm の印字幅と一致する。

# 以下 2 つは T02 実機の実測値 (2026-08-11)。
# 「A を印字 → ESC d 10 → B を印字 → ESC d 80」の 1 枚を出して、
# A/B 間と B/カッター間をノギスで測り、逆算した。別個体で紙送り量が
# 合わない場合はここだけ調整すればよい。
FEED_UNIT_DOTS = 20            # ESC d n の 1 単位 = 20 dots = 2.5mm

# 印字終了後、最終行がカッターバーを越えるまで送る量。15mm で最終行の
# 8mm 先にカッターが来たので、10mm で約 3mm 手前になる。逆算すると
# ヘッド〜カッターバーは約 9mm。減らしすぎると印字がカッターに届かず、
# 切り取っても文字が本体側に残る。
TEAR_OFF_FEED_MM = 10

# 印字速度の実測は約 38 lines/s (164 行の途中 119 行目で切断した回から逆算)。
# 待ち足りないと末尾が黙って欠落するだけで、待ちすぎても損は数秒なので
# 安全側に倒してある。
PRINT_LINES_PER_SEC = 25
DISCONNECT_MARGIN_SEC = 2.0

SCAN_TIMEOUT_SEC = 15.0

ESC = b"\x1b"
GS = b"\x1d"
US = b"\x1f"

# --------------------------------------------------------------------- output

DEBUG = False


def log(message: str) -> None:
    """--debug のときだけ出す詳細ログ。stderr なのでパイプを汚さない。"""
    if DEBUG:
        print(message, file=sys.stderr)


def step(message: str) -> None:
    """処理の区切り。進捗ドットと同じ行に続けるので改行しない。"""
    print(message, end="", flush=True)


def tick(mark: str = ".") -> None:
    """進捗 1 コマ。--debug 時は log() 側が詳細を出すので黙る。

    BLE は数秒〜十数秒待たされる場面が多く、無音だとフリーズと区別が
    つかないため、何か動いていることだけは常に見せる。
    """
    if not DEBUG:
        print(mark, end="", flush=True)


def done(message: str = "") -> None:
    """進捗行を閉じる。"""
    print(f" {message}" if message else "", flush=True)


@contextlib.asynccontextmanager
async def ticking(message: str, end: str = "") -> AsyncIterator[None]:
    """待っている間、1 秒ごとに進捗を出し続ける。

    BLE の接続は十数秒かかることがあり、無音だとフリーズと区別がつかない。
    """
    step(message)

    async def ticker() -> None:
        while True:
            await asyncio.sleep(1.0)
            tick()

    task = asyncio.create_task(ticker())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        done(end)


# ------------------------------------------------------------------- commands


def cmd_header(justify: int = 0, density: int = 4) -> bytes:
    """ESC @ / ESC a n / vendor density."""
    return (
        ESC + b"@"                        # initialize
        + ESC + b"a" + bytes([justify])   # 0=left 1=center 2=right
        + US + b"\x11\x02" + bytes([density])  # density: 0x01 / 0x03 / 0x04
    )


def cmd_footer(feed_mm: float = TEAR_OFF_FEED_MM) -> bytes:
    """紙送り + vendor status queries.

    既定値でちょうど最終行がカッターバーを越える。ここを削ると印字が
    ヘッドとカッターの間に残り、切り取れなくなる。
    """
    return (
        cmd_feed(feed_mm)
        + US + b"\x11\x08"   # battery / status
        + US + b"\x11\x0e"
        + US + b"\x11\x07"
        + US + b"\x11\x09"
    )


def cmd_feed(mm: float) -> bytes:
    """ESC d n — n は行数ではなく 20 dots 単位。255 を超えるぶんは分割する。

    mm 指定にしているのは、呼び出し側が dots や謎の「行」ではなく物理量で
    考えられるようにするため。
    """
    units = max(1, round(mm * DOTS_PER_MM / FEED_UNIT_DOTS))
    out = bytearray()
    while units > 0:
        n = min(255, units)
        out += ESC + b"d" + bytes([n])
        units -= n
    return bytes(out)


def cmd_raster(bitmap: bytes, lines: int) -> bytes:
    """GS v 0 — split into blocks of at most 255 lines."""
    out = bytearray()
    offset = 0
    remaining = lines
    while remaining > 0:
        n = min(MAX_LINES_PER_BLOCK, remaining)
        out += GS + b"v0" + b"\x00"                 # 1D 76 30 00 (mode 0)
        out += BYTES_PER_LINE.to_bytes(2, "little")  # xL xH
        out += n.to_bytes(2, "little")               # yL yH
        out += bitmap[offset : offset + n * BYTES_PER_LINE]
        offset += n * BYTES_PER_LINE
        remaining -= n
    return bytes(out)


# --------------------------------------------------------------- image → bits


def image_to_raster(
    img: Image.Image, width_dots: int = WIDTH_DOTS
) -> tuple[bytes, int]:
    """アスペクト比を保って width_dots 幅に合わせ、1bit 化する。

    拡大も行う。以前は縮小のみで、小さい画像は原寸のまま左に寄るだけ
    だった。width_dots が用紙幅より狭い場合は右側を白で埋める
    (ESC a 0 = 左寄せ設定に合わせる)。

    プリンタは bit=1 で黒く焼くが、PIL の "1" モードは 1 が白なので、
    量子化の前に輝度を反転させる。
    """
    img = img.convert("L")
    height = max(1, round(img.height * width_dots / img.width))
    img = img.resize((width_dots, height), Image.LANCZOS)

    if width_dots < WIDTH_DOTS:
        canvas = Image.new("L", (WIDTH_DOTS, height), 255)
        canvas.paste(img, (0, 0))
        img = canvas

    bw = ImageOps.invert(img).convert("1")  # Floyd–Steinberg dithering
    return bw.tobytes(), bw.height


AnyFont = ImageFont.FreeTypeFont | ImageFont.ImageFont

# 欧文は空白で、CJK は任意の字間で折り返せる。全角記号・かなも 1 字単位。
_CJK = "　-ヿ㐀-䶿一-鿿＀-￯"
_TOKEN_RE = re.compile(f"[{_CJK}]|[^{_CJK}\\s]+|\\s+")


def _split_oversized(token: str, font: AnyFont, max_width: int) -> list[str]:
    """1 行に収まらない単一トークン (長い URL など) を字単位で分割する。"""
    parts: list[str] = []
    current = ""
    for char in token:
        if current and font.getlength(current + char) > max_width:
            parts.append(current)
            current = char
        else:
            current += char
    if current:
        parts.append(current)
    return parts


def wrap_to_width(text: str, font: AnyFont, max_width: int) -> str:
    """Greedy word wrap measured in pixels, not characters.

    Character counting cannot work here: the font is proportional and CJK
    glyphs are twice as wide as latin ones, so the same 30 characters may be
    200 px or 800 px wide.
    """
    wrapped: list[str] = []
    for paragraph in text.split("\n"):
        line = ""
        for token in _TOKEN_RE.findall(paragraph):
            if not line and font.getlength(token) > max_width:
                *head, line = _split_oversized(token, font, max_width)
                wrapped += head
            elif line and font.getlength((line + token).rstrip()) > max_width:
                wrapped.append(line.rstrip())
                line = "" if token.isspace() else token
            else:
                line += token
        wrapped.append(line.rstrip())
    return "\n".join(wrapped)


def text_to_image(
    text: str,
    font_size: int = 28,
    margin: int = 8,
    width_dots: int = WIDTH_DOTS,
) -> Image.Image:
    """キャンバスは常に用紙全幅。width_dots は折り返し幅だけを狭める。"""
    font = _load_cjk_font(font_size)
    lines = wrap_to_width(text, font, width_dots - margin * 2).split("\n")

    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    line_h = max(
        probe.textbbox((0, 0), line or "A", font=font)[3] for line in lines
    ) + 6
    height = line_h * len(lines) + margin * 2

    img = Image.new("L", (WIDTH_DOTS, height), 255)
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        draw.text((margin, margin + i * line_h), line, font=font, fill=0)
    return img


def _load_cjk_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc",       # macOS
        "/System/Library/Fonts/Hiragino Sans GB.ttc",             # macOS
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Ubuntu
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


# ------------------------------------------------------------------ transport


async def _scan(
    timeout: float, stop_on: Callable[[BLEDevice], bool] | None = None
) -> tuple[dict[str, str | None], BLEDevice | None]:
    """timeout 秒スキャンし、機器を見つけるたびに進捗を 1 コマ出す。

    stop_on が真を返した時点で打ち切る。BleakScanner.discover() は必ず
    timeout を使い切るので、目的の機器が 1 秒で見つかっても待たされる。
    """
    hit: asyncio.Future[BLEDevice] = asyncio.get_running_loop().create_future()
    seen: dict[str, str | None] = {}

    def on_detect(device: BLEDevice, adv: AdvertisementData) -> None:
        if device.address not in seen:
            seen[device.address] = device.name
            tick()
            log(f"detected {device.address} rssi={adv.rssi} {device.name!r}")
        if stop_on is not None and not hit.done() and stop_on(device):
            hit.set_result(device)

    async with BleakScanner(detection_callback=on_detect):
        try:
            return seen, await asyncio.wait_for(hit, timeout)
        except TimeoutError:
            return seen, None


async def find_printer(
    prefix: str = DEVICE_NAME_PREFIX, timeout: float = SCAN_TIMEOUT_SEC
) -> BLEDevice | None:
    def matches(device: BLEDevice) -> bool:
        return bool(device.name and device.name.upper().startswith(prefix.upper()))

    step(f"scanning for {prefix} ")
    _, device = await _scan(timeout, matches)
    done(f"found {device.name} @ {device.address}" if device else "not found")
    return device


async def send_chunked(client: BleakClient, data: bytes) -> None:
    """ATT MTU で分割して送る。

    Write Request (response=True) を使う。Write Without Response には
    フロー制御がなく、溢れたぶんが黙って捨てられる。チャンクは MTU-3 に
    収めているので Long Write (Prepare/Execute) には落ちず、stall しない。
    """
    mtu = getattr(client, "mtu_size", None) or 23
    chunk = max(20, mtu - 3)
    total = -(-len(data) // chunk)
    log(f"mtu={mtu} chunk={chunk} chunks={total}")

    step(f"sending {len(data)} bytes ")
    for n, offset in enumerate(range(0, len(data), chunk), start=1):
        await client.write_gatt_char(CHAR_WRITE, data[offset : offset + chunk],
                                     response=True)
        tick()
        log(f"chunk {n}/{total}")
    done()


async def print_image(
    img: Image.Image,
    address: str | None = None,
    width_dots: int = WIDTH_DOTS,
) -> None:
    if address is None:
        device = await find_printer()
        if device is None:
            raise RuntimeError("T02 not found — is it powered on and unpaired from the app?")
        address = device.address

    bitmap, lines = image_to_raster(img, width_dots)
    payload = cmd_header() + cmd_raster(bitmap, lines) + cmd_footer()
    log(f"{img.width}x{img.height} -> {lines} lines, {len(payload)} bytes")

    client = BleakClient(address)
    async with ticking("connecting ", "ok"):
        await client.connect()

    try:
        try:
            await client.start_notify(
                CHAR_NOTIFY, lambda _h, d: log(f"notify: {d.hex(' ')}")
            )
        except Exception as exc:
            log(f"notify unavailable: {exc}")  # 必須ではないので続行する

        await send_chunked(client, payload)

        # 切断するとプリンタは未印字のバッファを捨てる。ACK は「受信した」
        # であって「印字し終えた」ではないので、物理的な印字時間ぶん待つ。
        wait = DISCONNECT_MARGIN_SEC + lines / PRINT_LINES_PER_SEC
        async with ticking(f"printing {wait:.1f}s ", "done"):
            await asyncio.sleep(wait)
    finally:
        await client.disconnect()


# ----------------------------------------------------------------------- main


STDIN_MARKER = "-"
MAX_WIDTH_MM = WIDTH_DOTS / DOTS_PER_MM


def parse_width(value: str) -> int:
    """"30mm" / "240px" / "240" を dots に変換する。単位なしは dots 扱い。"""
    text = value.strip().lower()
    for suffix, scale in (("mm", DOTS_PER_MM), ("dots", 1), ("dot", 1), ("px", 1)):
        if text.endswith(suffix):
            number, unit_scale = text[: -len(suffix)], scale
            break
    else:
        number, unit_scale = text, 1

    try:
        dots = round(float(number) * unit_scale)
    except ValueError:
        raise argparse.ArgumentTypeError(f"幅として解釈できない: {value!r}") from None

    if not 1 <= dots <= WIDTH_DOTS:
        raise argparse.ArgumentTypeError(
            f"幅は 1〜{WIDTH_DOTS} dots ({MAX_WIDTH_MM:.0f}mm) の範囲: {value!r}"
        )
    return dots


def _read_bytes(source: str) -> bytes:
    return sys.stdin.buffer.read() if source == STDIN_MARKER else Path(source).read_bytes()


def _read_text(source: str) -> str:
    return sys.stdin.read() if source == STDIN_MARKER else source


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="phomemo_t02",
        description="Phomemo T02 (BLE) minimal driver.",
        epilog=f'source を省略するか "-" を渡すと stdin から読む。'
               f" 用紙の最大印字幅は {WIDTH_DOTS} dots ({MAX_WIDTH_MM:.0f}mm)。",
    )
    parser.add_argument("mode", choices=("text", "image", "scan"))
    parser.add_argument("source", nargs="?", default=STDIN_MARKER,
                        help="印字する文字列 / 画像ファイル / \"-\" で stdin")
    parser.add_argument("--width", type=parse_width, default=WIDTH_DOTS,
                        metavar="30mm",
                        help="印字幅。既定はアスペクト比を保った全幅")
    parser.add_argument("--debug", action="store_true",
                        help="notify や chunk の詳細を stderr に出す")
    return parser


async def main() -> int:
    global DEBUG
    args = build_parser().parse_args()
    DEBUG = args.debug

    if args.mode == "scan":
        step(f"scanning {SCAN_TIMEOUT_SEC:.0f}s ")
        devices, _ = await _scan(SCAN_TIMEOUT_SEC)
        done(f"{len(devices)} devices")
        for address, name in devices.items():
            print(f"{address}  {name}")
        return 0

    if args.mode == "image":
        # BytesIO 経由にするのは、stdin が seek 不可で Image.open が失敗するため。
        source = Image.open(io.BytesIO(_read_bytes(args.source)))
        await print_image(source, width_dots=args.width)
        return 0

    text = _read_text(args.source).rstrip("\n")
    if not text.strip():
        print("nothing to print", file=sys.stderr)
        return 1
    await print_image(text_to_image(text, width_dots=args.width))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
