#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
"""List up global keyboard shortcuts on macOS and highlight conflicts.

Scans every source we can read without the Accessibility API and prints a
unified table of key combinations, grouped so that clashes are obvious.

Sources (inspired by HotkeyClash, https://github.com/Wunderlandmedia/HotkeyClash):
  * macOS system shortcuts .. com.apple.symbolichotkeys
  * Karabiner-Elements ...... ~/.config/karabiner/karabiner.json (key_code + pointing_button)
  * skhd .................... ~/.config/skhd/skhdrc
  * Hammerspoon ............. ~/.hammerspoon/**/*.lua (hs.hotkey.bind)
  * App preferences ......... ~/Library/Preferences/*.plist (keyCode + modifier pairs)

Note: global hotkeys that an app registers only at runtime (e.g. via
RegisterEventHotKey without persisting to prefs) cannot be seen from disk;
those require the Accessibility API. HotkeyClash covers them, this script does not.

Mouse buttons: only Karabiner records them on disk (via `pointing_button`), so
those are picked up. Mouse hotkeys owned by BetterTouchTool, Logi Options+ or
similar live in proprietary databases and are out of scope here.

Output is one binding per line (grep/awk friendly) by default:
    <combo>  <CONFLICT|>  [<source>] <owner> — <action>
Use --group for the old combo-grouped tree view.

Usage:
    ./listup_global_hotkey.py                 # one line per binding, mark conflicts
    ./listup_global_hotkey.py --group         # group by combo (tree view)
    ./listup_global_hotkey.py --conflicts     # show only conflicting combos
    ./listup_global_hotkey.py --key space     # filter to combos using a given key
"""

from __future__ import annotations

import argparse
import glob
import json
import plistlib
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

# --- Modifier bit masks -----------------------------------------------------
# NSEvent.ModifierFlags (device independent), as stored by most prefs / MASShortcut.
NS_SHIFT = 0x20000
NS_CONTROL = 0x40000
NS_OPTION = 0x80000
NS_COMMAND = 0x100000

# Carbon modifier flags, as stored in com.apple.symbolichotkeys.
CARBON_SHIFT = 0x20000
CARBON_CONTROL = 0x40000
CARBON_OPTION = 0x80000
CARBON_COMMAND = 0x100000
# The symbolichotkeys plist actually uses these Carbon-style bits:
#   shift 131072 / control 262144 / option 524288 / command 1048576
SYM_SHIFT = 131072
SYM_CONTROL = 262144
SYM_OPTION = 524288
SYM_COMMAND = 1048576

# Classic Carbon event modifier flags (used by MASShortcut, Dropover, and many
# apps that store hotkeys via RegisterEventHotKey). These are the small values.
CARBON_CMD = 0x0100      # 256
CARBON_SHIFT_C = 0x0200  # 512
CARBON_OPTION_C = 0x0800  # 2048
CARBON_CONTROL_C = 0x1000  # 4096

# --- Virtual key code -> display name ---------------------------------------
KEYCODE_NAME: dict[int, str] = {
    0x00: "A", 0x01: "S", 0x02: "D", 0x03: "F", 0x04: "H", 0x05: "G",
    0x06: "Z", 0x07: "X", 0x08: "C", 0x09: "V", 0x0B: "B", 0x0C: "Q",
    0x0D: "W", 0x0E: "E", 0x0F: "R", 0x10: "Y", 0x11: "T",
    0x1F: "O", 0x20: "U", 0x22: "I", 0x23: "P", 0x25: "L",
    0x26: "J", 0x28: "K", 0x2D: "N", 0x2E: "M",
    0x12: "1", 0x13: "2", 0x14: "3", 0x15: "4", 0x17: "5",
    0x16: "6", 0x1A: "7", 0x1C: "8", 0x19: "9", 0x1D: "0",
    0x24: "Return", 0x35: "Escape", 0x33: "Delete", 0x30: "Tab",
    0x31: "Space", 0x32: "`",
    0x1B: "-", 0x18: "=", 0x21: "[", 0x1E: "]", 0x2A: "\\",
    0x29: ";", 0x27: "'", 0x2B: ",", 0x2F: ".", 0x2C: "/",
    0x7B: "Left", 0x7C: "Right", 0x7D: "Down", 0x7E: "Up",
    0x7A: "F1", 0x78: "F2", 0x63: "F3", 0x76: "F4", 0x60: "F5",
    0x61: "F6", 0x62: "F7", 0x64: "F8", 0x65: "F9", 0x6D: "F10",
    0x67: "F11", 0x6F: "F12", 0x69: "F13", 0x6B: "F14", 0x71: "F15",
    0x74: "PageUp", 0x79: "PageDown", 0x73: "Home", 0x77: "End",
    0x75: "ForwardDelete",
}

# Mouse buttons live in a separate number space so they never collide with a
# keyboard virtual key code. Only Karabiner records these on disk, as
# `pointing_button` values ("button1" = left, "button2" = right, ...).
MOUSE_CODE_BASE = 0x10000
MOUSE_BUTTON_NAME: dict[int, str] = {
    1: "LeftClick", 2: "RightClick", 3: "MiddleClick",
}


def display_key(code: int) -> str:
    """Human name for a virtual key code or a MOUSE_CODE_BASE-offset mouse button."""
    if code >= MOUSE_CODE_BASE:
        n = code - MOUSE_CODE_BASE
        return MOUSE_BUTTON_NAME.get(n, f"Mouse{n}")
    return KEYCODE_NAME.get(code, f"key#{code}")

# Karabiner / skhd key name -> virtual key code (shared where names match).
KARABINER_KEYMAP: dict[str, int] = {
    "a": 0x00, "s": 0x01, "d": 0x02, "f": 0x03, "h": 0x04, "g": 0x05,
    "z": 0x06, "x": 0x07, "c": 0x08, "v": 0x09, "b": 0x0B, "q": 0x0C,
    "w": 0x0D, "e": 0x0E, "r": 0x0F, "y": 0x10, "t": 0x11,
    "o": 0x1F, "u": 0x20, "i": 0x22, "p": 0x23, "l": 0x25,
    "j": 0x26, "k": 0x28, "n": 0x2D, "m": 0x2E,
    "1": 0x12, "2": 0x13, "3": 0x14, "4": 0x15, "5": 0x17,
    "6": 0x16, "7": 0x1A, "8": 0x1C, "9": 0x19, "0": 0x1D,
    "return_or_enter": 0x24, "escape": 0x35, "delete_or_backspace": 0x33,
    "tab": 0x30, "spacebar": 0x31, "grave_accent_and_tilde": 0x32,
    "hyphen": 0x1B, "equal_sign": 0x18, "open_bracket": 0x21,
    "close_bracket": 0x1E, "backslash": 0x2A, "semicolon": 0x29,
    "quote": 0x27, "comma": 0x2B, "period": 0x2F, "slash": 0x2C,
    "left_arrow": 0x7B, "right_arrow": 0x7C, "down_arrow": 0x7D, "up_arrow": 0x7E,
    "f1": 0x7A, "f2": 0x78, "f3": 0x63, "f4": 0x76, "f5": 0x60,
    "f6": 0x61, "f7": 0x62, "f8": 0x64, "f9": 0x65, "f10": 0x6D,
    "f11": 0x67, "f12": 0x6F, "f13": 0x69, "f14": 0x6B, "f15": 0x71,
    "page_up": 0x74, "page_down": 0x79, "home": 0x73, "end": 0x77,
    "delete_forward": 0x75,
}
SKHD_KEYMAP: dict[str, int] = {
    **{k: v for k, v in KARABINER_KEYMAP.items() if len(k) == 1},
    "return": 0x24, "escape": 0x35, "delete": 0x33, "tab": 0x30, "space": 0x31,
    "-": 0x1B, "=": 0x18, "[": 0x21, "]": 0x1E, "\\": 0x2A, ";": 0x29,
    "'": 0x27, ",": 0x2B, ".": 0x2F, "/": 0x2C, "`": 0x32,
    "left": 0x7B, "right": 0x7C, "down": 0x7D, "up": 0x7E,
    "f1": 0x7A, "f2": 0x78, "f3": 0x63, "f4": 0x76, "f5": 0x60,
    "f6": 0x61, "f7": 0x62, "f8": 0x64, "f9": 0x65, "f10": 0x6D,
    "f11": 0x67, "f12": 0x6F, "f13": 0x69, "f14": 0x6B, "f15": 0x71,
    "pageup": 0x74, "pagedown": 0x79, "home": 0x73, "end": 0x77,
}

# Known symbolic hotkey IDs -> human readable names (from HotkeyClash).
SYMBOLIC_NAMES: dict[int, str] = {
    32: "Mission Control: All Windows",
    33: "Mission Control: Application Windows",
    34: "Mission Control: Show Desktop",
    36: "Move left a space", 37: "Move right a space",
    62: "Mission Control: Move left a space",
    63: "Mission Control: Move right a space",
    79: "Switch to Desktop 1", 80: "Switch to Desktop 2",
    81: "Switch to Desktop 3", 82: "Switch to Desktop 4",
    60: "Select previous input source", 61: "Select next input source",
    64: "Show Spotlight search", 65: "Show Finder search window",
    28: "Screenshot: Save picture of screen",
    29: "Screenshot: Copy picture of screen",
    30: "Screenshot: Save picture of selected area",
    31: "Screenshot: Copy picture of selected area",
    184: "Screenshot: Screenshot and recording options",
    118: "Focus Dock", 162: "Focus menu bar",
    163: "Focus next window (accessibility)",
    175: "Focus next window (accessibility)",
    164: "Focus floating window",
    27: "Move focus to next window", 51: "Move focus to status menus",
    57: "Turn keyboard access on or off",
    145: "Decrease display brightness", 144: "Increase display brightness",
    52: "Turn Dock hiding on/off",
    204: "Decrease keyboard brightness", 205: "Increase keyboard brightness",
    159: "Show Launchpad", 160: "Show Launchpad",
    175: "Notification Center", 190: "Do Not Disturb",
}


@dataclass(frozen=True)
class Hotkey:
    """A single global hotkey binding discovered from some source."""

    key_code: int
    modifiers: int  # normalized to NS_* bit layout
    owner: str
    action: str
    source: str

    @property
    def combo(self) -> str:
        parts: list[str] = []
        if self.modifiers & NS_CONTROL:
            parts.append("⌃")
        if self.modifiers & NS_OPTION:
            parts.append("⌥")
        if self.modifiers & NS_SHIFT:
            parts.append("⇧")
        if self.modifiers & NS_COMMAND:
            parts.append("⌘")
        parts.append(display_key(self.key_code))
        return "".join(parts)

    @property
    def combo_id(self) -> tuple[int, int]:
        return (self.key_code, self.modifiers)


def _sym_to_ns(carbon: int) -> int:
    """Convert symbolichotkeys modifier bits to the NS_* layout used here."""
    out = 0
    if carbon & SYM_SHIFT:
        out |= NS_SHIFT
    if carbon & SYM_CONTROL:
        out |= NS_CONTROL
    if carbon & SYM_OPTION:
        out |= NS_OPTION
    if carbon & SYM_COMMAND:
        out |= NS_COMMAND
    return out


def _normalize_modifiers(mods: int) -> int:
    """Normalize an arbitrary modifier value from app prefs to the NS_* layout.

    App preferences store modifiers in one of two conventions:
      * NSEvent.ModifierFlags — large bits (>= 0x10000), used as-is.
      * Classic Carbon event flags — small bits (cmd 256 / shift 512 /
        option 2048 / control 4096), used by RegisterEventHotKey-based apps.
    """
    if mods >= NS_SHIFT:  # already in NSEvent layout
        return mods & (NS_SHIFT | NS_CONTROL | NS_OPTION | NS_COMMAND)
    out = 0
    if mods & CARBON_CMD:
        out |= NS_COMMAND
    if mods & CARBON_SHIFT_C:
        out |= NS_SHIFT
    if mods & CARBON_OPTION_C:
        out |= NS_OPTION
    if mods & CARBON_CONTROL_C:
        out |= NS_CONTROL
    return out


# --- Scanners ----------------------------------------------------------------

def scan_system_shortcuts() -> list[Hotkey]:
    try:
        raw = subprocess.check_output(
            "defaults export com.apple.symbolichotkeys - | plutil -convert json -o - -",
            shell=True, stderr=subprocess.DEVNULL,
        )
        data = json.loads(raw)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return []

    result: list[Hotkey] = []
    for id_str, entry in data.get("AppleSymbolicHotKeys", {}).items():
        if not isinstance(entry, dict) or not entry.get("enabled"):
            continue
        params = entry.get("value", {}).get("parameters")
        if not isinstance(params, list) or len(params) < 3:
            continue
        key_code, carbon_mods = params[1], params[2]
        if not isinstance(key_code, int) or key_code == 0xFFFF:
            continue
        sid = int(id_str) if id_str.lstrip("-").isdigit() else -1
        result.append(Hotkey(
            key_code=key_code,
            modifiers=_sym_to_ns(carbon_mods),
            owner="macOS",
            action=SYMBOLIC_NAMES.get(sid, f"System shortcut #{id_str}"),
            source="system",
        ))
    return result


def scan_karabiner() -> list[Hotkey]:
    path = Path("~/.config/karabiner/karabiner.json").expanduser()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    profiles = data.get("profiles", [])
    profile = next((p for p in profiles if p.get("selected")), profiles[0] if profiles else None)
    if not profile:
        return []

    mod_map = {
        "command": NS_COMMAND, "left_command": NS_COMMAND, "right_command": NS_COMMAND,
        "shift": NS_SHIFT, "left_shift": NS_SHIFT, "right_shift": NS_SHIFT,
        "option": NS_OPTION, "left_option": NS_OPTION, "right_option": NS_OPTION,
        "control": NS_CONTROL, "left_control": NS_CONTROL, "right_control": NS_CONTROL,
    }
    result: list[Hotkey] = []
    rules = profile.get("complex_modifications", {}).get("rules", [])
    for rule in rules:
        desc = rule.get("description", "Karabiner rule")
        for manip in rule.get("manipulators", []):
            frm = manip.get("from", {})
            key_name = frm.get("key_code")
            pointing = frm.get("pointing_button")
            if key_name in KARABINER_KEYMAP:
                key_code = KARABINER_KEYMAP[key_name]
            elif isinstance(pointing, str) and pointing.startswith("button"):
                try:
                    key_code = MOUSE_CODE_BASE + int(pointing.removeprefix("button"))
                except ValueError:
                    continue
            else:
                continue
            mods = 0
            for mod in frm.get("modifiers", {}).get("mandatory", []):
                mods |= mod_map.get(mod, 0)
            result.append(Hotkey(
                key_code=key_code,
                modifiers=mods,
                owner="Karabiner-Elements",
                action=desc,
                source="karabiner",
            ))
    return result


def scan_skhd() -> list[Hotkey]:
    path = Path("~/.config/skhd/skhdrc").expanduser()
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []

    mod_map = {
        "cmd": NS_COMMAND, "shift": NS_SHIFT, "alt": NS_OPTION,
        "opt": NS_OPTION, "ctrl": NS_CONTROL,
    }
    result: list[Hotkey] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        hotkey_part, _, command = line.partition(":")
        hotkey_part, command = hotkey_part.strip(), command.strip()
        if " - " not in hotkey_part:
            continue
        mods_part, _, key_part = hotkey_part.rpartition(" - ")
        key = key_part.strip().lower()
        if key not in SKHD_KEYMAP:
            continue
        mods = 0
        for token in mods_part.split("+"):
            token = token.strip().lower()
            if token == "hyper":
                mods |= NS_COMMAND | NS_OPTION | NS_SHIFT | NS_CONTROL
            elif token == "meh":
                mods |= NS_OPTION | NS_SHIFT | NS_CONTROL
            else:
                mods |= mod_map.get(token, 0)
        result.append(Hotkey(
            key_code=SKHD_KEYMAP[key],
            modifiers=mods,
            owner="skhd",
            action=command,
            source="skhd",
        ))
    return result


def scan_hammerspoon() -> list[Hotkey]:
    root = Path("~/.hammerspoon").expanduser()
    if not root.is_dir():
        return []
    # hs.hotkey.bind({"cmd","alt"}, "space", fn) -- parse loosely.
    import re

    bind_re = re.compile(
        r"""hs\.hotkey\.bind\s*\(\s*(\{[^}]*\})\s*,\s*(["'][^"']*["'])""",
        re.IGNORECASE,
    )
    mod_map = {
        "cmd": NS_COMMAND, "command": NS_COMMAND, "shift": NS_SHIFT,
        "alt": NS_OPTION, "option": NS_OPTION, "ctrl": NS_CONTROL, "control": NS_CONTROL,
    }
    result: list[Hotkey] = []
    for lua in root.rglob("*.lua"):
        try:
            text = lua.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for mods_group, key_token in bind_re.findall(text):
            key = key_token.strip("\"'").lower()
            if key not in SKHD_KEYMAP and key not in KARABINER_KEYMAP:
                continue
            key_code = SKHD_KEYMAP.get(key) or KARABINER_KEYMAP.get(key)
            if key_code is None:
                continue
            mods = 0
            for token in re.findall(r"[a-zA-Z]+", mods_group):
                mods |= mod_map.get(token.lower(), 0)
            result.append(Hotkey(
                key_code=key_code,
                modifiers=mods,
                owner=f"Hammerspoon ({lua.name})",
                action=f'bind "{key}"',
                source="hammerspoon",
            ))
    return result


def _iter_preference_plists() -> "list[Path]":
    """All preference plists worth scanning: top level, ByHost, and app containers."""
    home = Path.home()
    patterns = [
        "Library/Preferences/*.plist",
        "Library/Preferences/ByHost/*.plist",
        "Library/Containers/*/Data/Library/Preferences/*.plist",
        "Library/Group Containers/*/Library/Preferences/*.plist",
    ]
    seen: dict[str, Path] = {}
    for pattern in patterns:
        for p in home.glob(pattern):
            seen[str(p)] = p
    return list(seen.values())


def scan_app_preferences() -> list[Hotkey]:
    """Best-effort scan of preference plists for stored keyCode+modifier pairs.

    Covers ~/Library/Preferences plus ByHost and sandboxed app containers, since
    many apps (MASShortcut / KeyboardShortcuts based) store their global hotkey
    there rather than at the top level.
    """
    key_fields = ("keyCode", "carbonKeyCode", "keycode", "HotKey Key Code")
    mod_fields = (
        "modifierFlags", "modifiers", "carbonModifiers", "modifierMask",
        "HotKey Modifier Flags",
    )
    # Dict-local flags that mean "this hotkey is turned off"; skip those combos.
    disabled_when_zero = ("Has Hotkey",)
    result: list[Hotkey] = []

    for plist_path in _iter_preference_plists():
        try:
            with plist_path.open("rb") as fh:
                data = plistlib.load(fh)
        except Exception:
            continue
        owner = plist_path.stem

        def walk(obj: object, trail: str) -> None:
            if isinstance(obj, dict):
                key_code = next(
                    (obj[f] for f in key_fields if isinstance(obj.get(f), int)), None
                )
                mods = next(
                    (obj[f] for f in mod_fields if isinstance(obj.get(f), int)), None
                )
                explicitly_off = any(
                    f in obj and not obj[f] for f in disabled_when_zero
                )
                if (
                    key_code is not None
                    and mods is not None
                    and key_code in KEYCODE_NAME
                    and not explicitly_off
                ):
                    normalized = _normalize_modifiers(mods)
                    result.append(Hotkey(
                        key_code=key_code,
                        modifiers=normalized,
                        owner=owner,
                        action=trail.lstrip("/") or "shortcut",
                        source="app-prefs",
                    ))
                for k, v in obj.items():
                    walk(v, f"{trail}/{k}")
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    walk(v, f"{trail}[{i}]")

        walk(data, "")
    return result


# --- Reporting ---------------------------------------------------------------

def collect_all() -> list[Hotkey]:
    hotkeys: list[Hotkey] = []
    hotkeys += scan_system_shortcuts()
    hotkeys += scan_karabiner()
    hotkeys += scan_skhd()
    hotkeys += scan_hammerspoon()
    hotkeys += scan_app_preferences()
    return hotkeys


def _is_conflict(group: list[Hotkey]) -> bool:
    return len({(h.owner, h.action) for h in group}) > 1


def report(
    hotkeys: list[Hotkey], *, conflicts_only: bool, key_filter: str | None, grouped_view: bool
) -> None:
    if key_filter:
        wanted = key_filter.strip().lower()
        wanted_code = SKHD_KEYMAP.get(wanted) or KARABINER_KEYMAP.get(wanted)
        hotkeys = [
            h for h in hotkeys
            if (wanted_code is not None and h.key_code == wanted_code)
            or display_key(h.key_code).lower() == wanted
        ]

    grouped: dict[tuple[int, int], list[Hotkey]] = defaultdict(list)
    for hk in hotkeys:
        grouped[hk.combo_id].append(hk)

    ordered = sorted(
        grouped.items(),
        key=lambda kv: (-len(kv[1]), kv[0][0], kv[0][1]),
    )

    printed_combos = 0
    for _combo_id, group in ordered:
        is_conflict = _is_conflict(group)
        if conflicts_only and not is_conflict:
            continue
        if grouped_view:
            marker = "⚠️  CONFLICT" if is_conflict else ""
            print(f"{group[0].combo:<12} {marker}")
            for hk in group:
                print(f"    [{hk.source:<10}] {hk.owner} — {hk.action}")
            print()
        else:
            # One self-contained line per binding: the combo is repeated on
            # every line so `grep <combo>` / `grep <owner>` always shows it all.
            flag = "CONFLICT" if is_conflict else ""
            for hk in group:
                print(f"{hk.combo:<14} {flag:<8} [{hk.source:<10}] {hk.owner} — {hk.action}")
        printed_combos += 1

    if printed_combos == 0:
        print("(該当するホットキーは見つかりませんでした)")
        return
    conflict_count = sum(1 for _, g in ordered if _is_conflict(g))
    print(f"── {printed_combos} combo(s) shown, {conflict_count} conflict(s) ──")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--conflicts", action="store_true", help="show only conflicting combos")
    parser.add_argument("--key", metavar="NAME", help="filter to a key (e.g. space, a, f1)")
    parser.add_argument(
        "--group", action="store_true",
        help="group by combo (tree view) instead of one line per binding",
    )
    args = parser.parse_args()

    hotkeys = collect_all()
    if not hotkeys:
        print("ホットキーを1件も検出できませんでした。", file=sys.stderr)
        return 1
    report(
        hotkeys,
        conflicts_only=args.conflicts,
        key_filter=args.key,
        grouped_view=args.group,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
