#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///

"""
Network Diagnostic Tool
Checks network connectivity step by step for macOS and Ubuntu
"""

from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from lib.progressbar import LiveLine
from lib.termcolor import (BRIGHT_BLACK, BRIGHT_BLUE, BRIGHT_CYAN, BRIGHT_GREEN,
                           BRIGHT_RED, BRIGHT_WHITE, BRIGHT_YELLOW, bold,
                           color_enabled, paint16, set_color_mode)
from lib.termtext import pad_display

# Everything the script prints is its report, so it all goes to one stream
# (the spinner line has to share it, see lib/progressbar.LiveLine).
OUT = sys.stdout

# Display width of the check-name column in a result line.
NAME_WIDTH = 28

# Lines of `details` shown per result with --verbose.
DETAIL_LINES = 5

# Width of the pass/warn/fail proportion bar in the summary.
SUMMARY_BAR_WIDTH = 40

# Seconds to wait for the system resolver before calling a lookup hung.
RESOLVE_TIMEOUT = 5.0

SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
SPINNER_FPS = 12.0

# Labels for the kinds of interface, used to tell wired from Wi-Fi.
KIND_WIRED = "有線"
KIND_WIFI = "Wi-Fi"
KIND_VPN = "VPN"
KIND_BRIDGE = "ブリッジ"
KIND_VIRTUAL = "仮想"


class CheckStatus(Enum):
    """Status of each check, as (symbol, color, severity for "worst of")."""
    PASS = ("✓", BRIGHT_GREEN, 1)
    INFO = ("ℹ", BRIGHT_BLUE, 0)
    WARN = ("⚠", BRIGHT_YELLOW, 2)
    FAIL = ("✗", BRIGHT_RED, 3)
    SKIP = ("○", BRIGHT_WHITE, 0)

    @property
    def symbol(self) -> str:
        return self.value[0]

    @property
    def color(self) -> int:
        return self.value[1]

    @property
    def severity(self) -> int:
        return self.value[2]

    def colored(self, text: str | None = None) -> str:
        """The symbol (or `text`) in this status's color, plain when color is off."""
        return paint16(self.symbol if text is None else text, self.color, OUT)


class Stage(Enum):
    """Hops on the way out, drawn as the path diagram in the summary."""
    LOCAL = "この端末"
    GATEWAY = "ゲートウェイ"
    INTERNET = "インターネット"
    DNS = "名前解決"
    HTTPS = "HTTPS"


@dataclass
class CheckResult:
    """Result of a single check"""
    name: str
    status: CheckStatus
    message: str
    details: str | None = None
    stage: Stage | None = None


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def last_line(self) -> str:
        """Last non-empty output line, from either stream (for error messages)."""
        lines = [line.strip() for line in (self.stdout + "\n" + self.stderr).splitlines()]
        lines = [line for line in lines if line]
        return lines[-1] if lines else f"終了コード {self.returncode}"


@dataclass
class PingStats:
    reachable: bool
    loss_percent: float | None
    avg_ms: float | None
    output: str

    def status(self) -> CheckStatus:
        if not self.reachable or self.loss_percent == 100.0:
            return CheckStatus.FAIL
        if self.loss_percent is not None and self.loss_percent > 0:
            return CheckStatus.WARN
        return CheckStatus.PASS

    def summary(self) -> str:
        if not self.reachable:
            return "応答なし"
        parts = []
        if self.avg_ms is not None:
            parts.append(f"平均 {self.avg_ms:.1f} ms")
        if self.loss_percent is not None:
            parts.append(f"損失 {self.loss_percent:g}%")
        return "  ".join(parts) if parts else "応答あり"


@dataclass
class DefaultRoute:
    gateway: str | None     # None for a device-only route (`default dev wg0`)
    interface: str | None
    scoped: bool            # macOS interface-scoped route (flag I): not the primary


class Spinner(LiveLine):
    """The "now checking ..." line shown while a slow check runs."""

    def __init__(self, enabled: bool) -> None:
        super().__init__(enabled=enabled, stream=OUT, fps=SPINNER_FPS, animate=enabled)
        self.label = ""

    def parts(self) -> list[str]:
        if not self.label:
            return [""]
        frame = SPINNER_FRAMES[int((time.monotonic() - self.started) * SPINNER_FPS)
                               % len(SPINNER_FRAMES)]
        return [f"  {paint16(frame, BRIGHT_CYAN, OUT)}", paint16(self.label, BRIGHT_BLACK, OUT)]

    def set_label(self, label: str) -> None:
        with self.lock:
            self.label = label
        self.refresh()


def run_command(cmd: list[str], timeout: float = 5) -> CommandResult:
    """Run a command and capture its output; failures to start become a result too."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return CommandResult(result.returncode, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return CommandResult(-1, "", f"{timeout:g} 秒でタイムアウト")
    except OSError as e:
        return CommandResult(-1, "", str(e))


def resolve_with_timeout(domain: str, timeout: float = RESOLVE_TIMEOUT) -> str:
    """socket.gethostbyname with a deadline.

    The system resolver cannot be interrupted, so the lookup runs in a daemon
    thread that is simply abandoned if it hangs (it must not hold up exit).
    """
    outcome: dict[str, str | BaseException] = {}

    def lookup() -> None:
        try:
            outcome["ip"] = socket.gethostbyname(domain)
        except OSError as e:
            outcome["error"] = e

    thread = threading.Thread(target=lookup, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        raise TimeoutError(f"{timeout:g} 秒以内に応答がありません")
    if "error" in outcome:
        raise outcome["error"]  # type: ignore[misc]
    return str(outcome["ip"])


def detect_container() -> bool:
    """Detect if running inside a container (Docker, Podman, Kubernetes)."""
    if Path("/.dockerenv").exists() or Path("/run/.containerenv").exists():
        return True
    try:
        cgroup = Path("/proc/1/cgroup").read_text(encoding="utf-8")
    except OSError:
        return False
    # cgroup v1 names the runtime here; under cgroup v2 it is usually just "0::/"
    return any(word in cgroup for word in ("docker", "containerd", "kubepods", "libpod"))


class NetworkChecker:
    """Main network diagnostic checker"""

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose
        self.results: list[CheckResult] = []
        self.is_macos = platform.system() == "Darwin"
        self.is_container = detect_container()
        self.spinner = Spinner(enabled=OUT.isatty())
        self._interface_kinds: dict[str, str] | None = None

        # Test targets
        self.test_server = "www.kcrt.net"
        self.test_server_ip = "219.94.243.204"
        self.test_url = "https://profile.kcrt.net/"

    # -- output ---------------------------------------------------------------

    def _section(self, title: str) -> None:
        self.spinner.report("")
        self.spinner.report(f"{paint16('▍', BRIGHT_CYAN, OUT)}{bold(title, OUT)}")

    def _add_result(self, name: str, status: CheckStatus, message: str,
                    details: str | None = None, stage: Stage | None = None) -> None:
        """Record a result and print it right away under the current section."""
        result = CheckResult(name, status, message, details if self.verbose else None, stage)
        self.results.append(result)
        self.spinner.report(f"  {status.colored()}  {pad_display(name, NAME_WIDTH)} {message}")
        if result.details:
            lines = result.details.rstrip().splitlines()
            for line in lines[:DETAIL_LINES]:
                self.spinner.report(paint16(f"       │ {line}", BRIGHT_BLACK, OUT))
            if len(lines) > DETAIL_LINES:
                self.spinner.report(paint16("       │ …", BRIGHT_BLACK, OUT))

    def _run(self, label: str, cmd: list[str], timeout: float = 5) -> CommandResult:
        self.spinner.set_label(label)
        try:
            return run_command(cmd, timeout)
        finally:
            self.spinner.set_label("")

    # -- helpers --------------------------------------------------------------

    def _ping(self, host: str, count: int, ipv6: bool = False) -> PingStats:
        """Ping with a deadline, so an unreachable host cannot stall the run."""
        deadline = count + 2
        if self.is_macos:
            # macOS ping6 has no overall deadline option; the subprocess timeout covers it
            cmd = (['ping6', '-c', str(count), host] if ipv6
                   else ['ping', '-c', str(count), '-t', str(deadline), host])
        else:
            cmd = ['ping', '-6' if ipv6 else '-4', '-c', str(count), '-w', str(deadline), host]
        result = self._run(f"ping {host}", cmd, timeout=deadline + 3)

        # macOS prints "100.0% packet loss", Linux "100% packet loss"
        loss_match = re.search(r'([\d.]+)% packet loss', result.stdout)
        # macOS: "round-trip min/avg/max/stddev = a/b/c/d", Linux: "rtt min/avg/max/mdev = ..."
        avg_match = re.search(r'= [\d.]+/([\d.]+)/', result.stdout)
        return PingStats(
            reachable=result.ok,
            loss_percent=float(loss_match.group(1)) if loss_match else None,
            avg_ms=float(avg_match.group(1)) if avg_match else None,
            output=result.stdout or result.stderr,
        )

    def _interface_kind(self, interface: str) -> str:
        """Human label for an interface: Wi-Fi / 有線 / VPN / ..., else its own name."""
        if self._interface_kinds is None:
            self._interface_kinds = (self._macos_hardware_ports() if self.is_macos else {})
        if interface in self._interface_kinds:
            return self._interface_kinds[interface]
        if re.match(r'(utun|ipsec|ppp|tun|tap|wg)\d*', interface):
            return KIND_VPN
        if re.match(r'(bridge|br-|docker|virbr|veth|vnic|anpi)', interface):
            return KIND_BRIDGE if interface.startswith("bridge") else KIND_VIRTUAL
        if not self.is_macos:
            if Path(f"/sys/class/net/{interface}/wireless").exists():
                return KIND_WIFI
            if Path(f"/sys/class/net/{interface}/device").exists():
                return KIND_WIRED
        return interface

    def _macos_hardware_ports(self) -> dict[str, str]:
        """Map enX to Wi-Fi / 有線 from `networksetup` (empty if it is unavailable)."""
        result = run_command(['networksetup', '-listallhardwareports'])
        kinds: dict[str, str] = {}
        for port, device in re.findall(r'Hardware Port: (.+)\nDevice: (\S+)', result.stdout):
            if port == "Wi-Fi":
                kinds[device] = KIND_WIFI
            elif "Bridge" in port:
                kinds[device] = KIND_BRIDGE
            elif re.search(r'Ethernet|LAN|Thunderbolt', port):
                kinds[device] = KIND_WIRED
            else:
                kinds[device] = port
        return kinds

    def _describe_interface(self, interface: str | None) -> str:
        if not interface:
            return "インターフェース不明"
        kind = self._interface_kind(interface)
        return interface if kind == interface else f"{kind} ({interface})"

    # -- checks ---------------------------------------------------------------

    def check_container_environment(self) -> None:
        """Check container environment"""
        self._section("実行環境")

        if self.is_container:
            self._add_result("コンテナ", CheckStatus.INFO,
                             "コンテナ内で実行中（一部のチェックは制限されます）")
        else:
            self._add_result("コンテナ", CheckStatus.INFO, "ホスト上で実行中")

    def check_network_interfaces(self) -> None:
        """List interfaces that are up and have an IPv4 address"""
        self._section("インターフェース")

        if self.is_macos:
            result = self._run("ifconfig", ['ifconfig'])
            active = self._parse_macos_interfaces(result.stdout)
        else:
            result = self._run("ip addr", ['ip', '-o', '-4', 'addr', 'show', 'up'])
            active = self._parse_linux_interfaces(result.stdout)

        if not result.ok:
            self._add_result("インターフェース", CheckStatus.FAIL,
                             f"情報を取得できません: {result.last_line()}", stage=Stage.LOCAL)
            return
        if not active:
            self._add_result("インターフェース", CheckStatus.FAIL,
                             "IPv4 アドレスを持つ有効なインターフェースがありません",
                             result.stdout, stage=Stage.LOCAL)
            return
        for interface, addresses in active.items():
            # Bridges and virtual links (VM, container) are worth listing, but they are
            # not what gets this machine online
            kind = self._interface_kind(interface)
            status = CheckStatus.INFO if kind in (KIND_BRIDGE, KIND_VIRTUAL) else CheckStatus.PASS
            self._add_result(self._describe_interface(interface), status,
                             ", ".join(addresses), stage=Stage.LOCAL)

    @staticmethod
    def _parse_macos_interfaces(ifconfig: str) -> dict[str, list[str]]:
        """Interfaces with an IPv4 address that are not reported inactive (no lo0)."""
        active: dict[str, list[str]] = {}
        for block in re.split(r'\n(?=\S)', ifconfig):
            name_match = re.match(r'([\w.-]+):', block)
            if not name_match or name_match.group(1).startswith("lo"):
                continue
            # Point-to-point links (utun) have no status line; only an explicit inactive counts
            if "status: inactive" in block:
                continue
            addresses = re.findall(r'\tinet (\d+\.\d+\.\d+\.\d+)', block)
            if addresses:
                active[name_match.group(1)] = addresses
        return active

    @staticmethod
    def _parse_linux_interfaces(ip_addr: str) -> dict[str, list[str]]:
        """From `ip -o -4 addr show up`: "2: eth0    inet 10.0.0.2/24 ..." (no lo)."""
        active: dict[str, list[str]] = {}
        for name, address in re.findall(r'^\d+:\s+([^\s:@]+)\s+inet (\S+)', ip_addr, re.MULTILINE):
            if name != "lo":
                active.setdefault(name, []).append(address)
        return active

    def check_routing_table(self) -> str | None:
        """Check the default route; returns the gateway address to ping"""
        self._section("経路")

        if self.is_macos:
            result = self._run("netstat -rn", ['netstat', '-rn', '-f', 'inet'])
            routes = self._parse_macos_default_routes(result.stdout)
        else:
            result = self._run("ip route", ['ip', 'route', 'show', 'default'])
            routes = self._parse_linux_default_routes(result.stdout)

        if not result.ok:
            self._add_result("デフォルトゲートウェイ", CheckStatus.FAIL,
                             f"経路表を取得できません: {result.last_line()}", stage=Stage.LOCAL)
            return None
        if not routes:
            self._add_result("デフォルトゲートウェイ", CheckStatus.FAIL,
                             "有効なデフォルトゲートウェイがありません", result.stdout,
                             stage=Stage.LOCAL)
            return None

        # The unscoped route is the one macOS sends through; on Linux the kernel
        # lists the lowest metric first.
        primary = next((route for route in routes if not route.scoped), routes[0])
        self._add_result("デフォルトゲートウェイ", CheckStatus.PASS,
                         f"{primary.gateway or '(直結)'}  {self._describe_interface(primary.interface)}",
                         result.stdout, stage=Stage.LOCAL)

        others = [route for route in routes if route is not primary]
        if others:
            self._report_other_routes(primary, others)
        return primary.gateway

    def _report_other_routes(self, primary: DefaultRoute, others: list[DefaultRoute]) -> None:
        """Say when more than one interface has a way out, e.g. wired and Wi-Fi both up."""
        kinds = {self._interface_kind(route.interface or "") for route in [primary, *others]}
        if {KIND_WIRED, KIND_WIFI} <= kinds:
            name = "有線と Wi-Fi の両方に接続"
        else:
            name = "複数の経路に接続"
        standby = ", ".join(f"{self._describe_interface(route.interface)} → {route.gateway or '(直結)'}"
                            for route in others)
        self._add_result(name, CheckStatus.INFO,
                         f"優先: {self._describe_interface(primary.interface)}  待機: {standby}")

    @staticmethod
    def _parse_macos_default_routes(netstat: str) -> list[DefaultRoute]:
        """From `netstat -rn -f inet`: "default  192.168.0.1  UGScg  en0  [expire]"."""
        routes: list[DefaultRoute] = []
        seen_interfaces: set[str] = set()
        for match in re.finditer(r'^default\s+(\S+)\s+(\S+)\s+(\S+)(.*)$', netstat, re.MULTILINE):
            gateway, flags, interface, rest = match.groups()
            # link# gateways, reject routes ('!') and 0.0.0.0 carry no traffic out
            if gateway.startswith('link#') or '!' in rest or gateway == '0.0.0.0':
                continue
            if interface in seen_interfaces:
                continue
            seen_interfaces.add(interface)
            routes.append(DefaultRoute(gateway, interface, scoped='I' in flags))
        return routes

    @staticmethod
    def _parse_linux_default_routes(ip_route: str) -> list[DefaultRoute]:
        """From `ip route show default`: "default via X dev Y ..." or "default dev wg0 ..."."""
        routes: list[DefaultRoute] = []
        for match in re.finditer(r'^default(?: via (\S+))?(?:.*? dev (\S+))?', ip_route, re.MULTILINE):
            gateway, interface = match.groups()
            if gateway == '0.0.0.0':
                continue
            if gateway or interface:
                routes.append(DefaultRoute(gateway, interface, scoped=False))
        return routes

    def check_dns_configuration(self) -> list[str]:
        """Check DNS configuration"""
        self._section("DNS 設定")

        dns_servers: list[str] = []
        if self.is_macos:
            result = self._run("scutil --dns", ['scutil', '--dns'])
            if result.ok:
                dns_servers = re.findall(r'nameserver\[\d+\] : (\S+)', result.stdout)
        else:
            try:
                content = Path('/etc/resolv.conf').read_text(encoding="utf-8")
                dns_servers = re.findall(r'^nameserver\s+(\S+)', content, re.MULTILINE)
            except OSError as e:
                self._add_result("/etc/resolv.conf", CheckStatus.FAIL, f"読めません: {e}",
                                 stage=Stage.DNS)

        # scutil lists the same server once per resolver (default, scoped, ...)
        dns_servers = list(dict.fromkeys(dns_servers))
        if dns_servers:
            self._add_result("DNS サーバー", CheckStatus.PASS,
                             f"{len(dns_servers)} 台: {', '.join(dns_servers[:3])}"
                             + (" …" if len(dns_servers) > 3 else ""), stage=Stage.DNS)
        else:
            self._add_result("DNS サーバー", CheckStatus.WARN, "見つかりません", stage=Stage.DNS)
        return dns_servers

    def check_ping_localhost(self) -> None:
        """Ping localhost"""
        self._section("疎通（ping）")
        stats = self._ping('127.0.0.1', count=3)
        self._add_result("localhost", stats.status(), stats.summary(), stats.output,
                         stage=Stage.LOCAL)

    def check_ping_gateway(self, gateway: str | None) -> None:
        """Ping default gateway"""
        if not gateway:
            self._add_result("ゲートウェイ", CheckStatus.SKIP,
                             "ping するゲートウェイのアドレスがありません", stage=Stage.GATEWAY)
            return
        stats = self._ping(gateway, count=4)
        status, message = stats.status(), stats.summary()
        # Many routers (and iPhone tethering) drop ICMP to themselves. If traffic
        # gets past them anyway, the silence is the router's policy, not a fault.
        if status == CheckStatus.FAIL and self._ping('1.1.1.1', count=1).reachable:
            status, message = CheckStatus.WARN, "ping に応答しない（外部へは届いている）"
        self._add_result(f"ゲートウェイ {gateway}", status, message,
                         stats.output, stage=Stage.GATEWAY)

    def check_ping_external(self) -> None:
        """Ping external servers"""
        test_servers = [
            ("Google DNS", "8.8.8.8"),
            ("Cloudflare DNS", "1.1.1.1"),
            ("KCRT Server", self.test_server_ip),
        ]
        for name, ip in test_servers:
            stats = self._ping(ip, count=3)
            self._add_result(f"{name} {ip}", stats.status(), stats.summary(), stats.output,
                             stage=Stage.INTERNET)

    def check_dns_resolution(self, dns_servers: list[str]) -> None:
        """Check DNS resolution"""
        self._section("名前解決")

        test_domains = ["google.com", self.test_server]
        for domain in test_domains:
            self.spinner.set_label(f"resolve {domain}")
            try:
                ip = resolve_with_timeout(domain)
                self._add_result(domain, CheckStatus.PASS, f"→ {ip}", stage=Stage.DNS)
            except (OSError, TimeoutError) as e:
                self._add_result(domain, CheckStatus.FAIL, f"解決できません: {e}", stage=Stage.DNS)
            finally:
                self.spinner.set_label("")

        # Ask each configured server directly, to tell a dead server from a dead resolver
        for dns_server in dns_servers[:2]:
            result = self._run(f"nslookup via {dns_server}",
                               ['nslookup', '-timeout=3', 'google.com', dns_server], timeout=10)
            # Both the server line and the answer say "Address:"; only an answer says "Name:"
            if result.ok and re.search(r'^Name:', result.stdout, re.MULTILINE):
                self._add_result(f"問い合わせ {dns_server}", CheckStatus.PASS, "応答あり",
                                 result.stdout, stage=Stage.DNS)
            else:
                self._add_result(f"問い合わせ {dns_server}", CheckStatus.FAIL,
                                 f"失敗: {result.last_line()}", result.stdout, stage=Stage.DNS)

    def check_http_connectivity(self) -> None:
        """Check HTTP/HTTPS connectivity"""
        self._section("HTTPS")

        if shutil.which('curl') is None:
            self._add_result("HTTPS 接続", CheckStatus.SKIP, "curl がありません", stage=Stage.HTTPS)
            return

        result = self._run(f"curl {self.test_url}",
                           ['curl', '-sS', '-o', '/dev/null', '-w', '%{http_code}|%{time_total}',
                            '--max-time', '10', self.test_url], timeout=15)
        name = self.test_url.removeprefix("https://").rstrip("/")
        if not result.ok:
            self._add_result(name, CheckStatus.FAIL, f"接続できません: {result.last_line()}",
                             stage=Stage.HTTPS)
        elif match := re.fullmatch(r'(\d{3})\|([\d.]+)', result.stdout.strip()):
            status_code, seconds = match.group(1), float(match.group(2))
            if status_code[0] in "23":
                self._add_result(name, CheckStatus.PASS, f"HTTP {status_code}  {seconds:.2f} 秒",
                                 stage=Stage.HTTPS)
            else:
                self._add_result(name, CheckStatus.WARN,
                                 f"接続はできたが HTTP {status_code}", stage=Stage.HTTPS)
        else:
            self._add_result(name, CheckStatus.WARN,
                             f"curl の出力を読めません: {result.stdout.strip()!r}", stage=Stage.HTTPS)

        if self.verbose:
            result = self._run("TLS handshake", ['curl', '-v', '-o', '/dev/null', '--max-time', '10',
                                                 self.test_url], timeout=15)
            if result.ok:
                self._add_result("TLS ハンドシェイク", CheckStatus.PASS, "成功", result.stderr,
                                 stage=Stage.HTTPS)

    def check_ipv6(self) -> None:
        """Check IPv6 connectivity"""
        self._section("IPv6")

        if self.is_macos:
            result = self._run("ifconfig", ['ifconfig'])
        else:
            result = self._run("ip -6 addr", ['ip', '-6', 'addr', 'show'])

        if result.ok:
            addresses = list(dict.fromkeys(re.findall(r'inet6 ([\da-f:]+)', result.stdout)))
            link_local = [a for a in addresses if a.startswith('fe80:')]
            # fc00::/7 is unique-local: routable inside a site only
            global_addresses = [a for a in addresses
                                if a != '::1' and not a.startswith(('fe80:', 'fc', 'fd'))]
            if global_addresses:
                self._add_result("グローバルアドレス", CheckStatus.PASS,
                                 f"{len(global_addresses)} 個")
            else:
                self._add_result("グローバルアドレス", CheckStatus.WARN, "ありません")
            if link_local:
                self._add_result("リンクローカル", CheckStatus.INFO, f"{len(link_local)} 個")

        stats = self._ping('google.com', count=2, ipv6=True)
        if stats.status() == CheckStatus.FAIL:
            self._add_result("IPv6 疎通", CheckStatus.WARN, "IPv6 では届きません")
        else:
            self._add_result("IPv6 疎通", stats.status(), stats.summary(), stats.output)

    def check_docker_specific(self) -> None:
        """Docker-specific checks"""
        if not self.is_container:
            return
        self._section("コンテナ固有")

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(2)
                sock.connect(('127.0.0.11', 53))
            self._add_result("Docker 内蔵 DNS", CheckStatus.PASS, "127.0.0.11 に接続可")
        except OSError:
            self._add_result("Docker 内蔵 DNS", CheckStatus.WARN, "127.0.0.11 に接続できません")

        try:
            self._add_result("ネットワーク名前空間", CheckStatus.INFO, os.readlink('/proc/self/ns/net'))
        except OSError:
            pass

    def check_firewall(self) -> None:
        """Report the firewall state (informational: on or off is not a fault)"""
        self._section("ファイアウォール")

        if self.is_macos:
            result = self._run("socketfilterfw",
                               ['/usr/libexec/ApplicationFirewall/socketfilterfw', '--getglobalstate'])
            # "Firewall is enabled. (State = 1)"; 2 means "block all incoming"
            match = re.search(r'State = (\d)', result.stdout)
            if not match:
                self._add_result("アプリケーション FW", CheckStatus.SKIP,
                                 f"状態を読めません: {result.last_line()}")
            else:
                state = {"0": "無効", "1": "有効", "2": "有効（外部からの接続をすべて遮断）"}
                self._add_result("アプリケーション FW", CheckStatus.INFO,
                                 state.get(match.group(1), f"State = {match.group(1)}"))
        else:
            result = self._run("iptables", ['sudo', '-n', 'iptables', '-L', '-n'])
            if result.ok:
                rules = [line for line in result.stdout.splitlines()
                         if line and not line.startswith(("Chain", "target"))]
                self._add_result("iptables", CheckStatus.INFO, f"ルール {len(rules)} 行",
                                 result.stdout)
            else:
                self._add_result("iptables", CheckStatus.SKIP, "確認できません（sudo が必要）")

    # -- summary --------------------------------------------------------------

    def _stage_status(self, stage: Stage) -> CheckStatus:
        statuses = [r.status for r in self.results
                    if r.stage == stage and r.status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.FAIL)]
        return max(statuses, key=lambda s: s.severity) if statuses else CheckStatus.SKIP

    def _path_diagram(self) -> str:
        """"✓ この端末 ━━ ⚠ ゲートウェイ ━━ ✗ インターネット ╌╌ ..."

        Each link takes the status of the hop it leads to: solid when that hop
        answered, dashed when it failed or was not tested.
        """
        pieces: list[str] = []
        for stage in Stage:
            status = self._stage_status(stage)
            if pieces:
                solid = status in (CheckStatus.PASS, CheckStatus.WARN)
                pieces.append(status.colored("━━" if solid else "╌╌"))
            pieces.append(f"{status.colored()} {status.colored(stage.value)}")
        return " ".join(pieces)

    def _proportion_bar(self, counts: dict[CheckStatus, int]) -> str:
        """A bar split by status, in their colors. Empty without color (nothing to tell apart)."""
        total = sum(counts.values())
        if not total or not color_enabled(OUT):
            return ""
        cells: list[str] = []
        remaining = SUMMARY_BAR_WIDTH
        ordered = [s for s in (CheckStatus.PASS, CheckStatus.INFO, CheckStatus.WARN,
                               CheckStatus.FAIL, CheckStatus.SKIP) if counts[s]]
        for index, status in enumerate(ordered):
            width = (remaining if index == len(ordered) - 1
                     else max(1, round(SUMMARY_BAR_WIDTH * counts[status] / total)))
            width = min(width, remaining)
            remaining -= width
            cells.append(status.colored("█" * width))
        return "".join(cells)

    def print_summary(self) -> int:
        """Print the path diagram and counts; returns the exit code"""
        rule = paint16("─" * 64, BRIGHT_BLACK, OUT)
        self.spinner.report("")
        self.spinner.report(rule)
        self.spinner.report(f"  {self._path_diagram()}")
        self.spinner.report("")

        counts = {status: sum(1 for r in self.results if r.status == status) for status in CheckStatus}
        labels = {CheckStatus.PASS: "成功", CheckStatus.WARN: "警告", CheckStatus.FAIL: "失敗",
                  CheckStatus.INFO: "情報", CheckStatus.SKIP: "省略"}
        tally = "  ".join(status.colored(f"{status.symbol} {labels[status]} {counts[status]}")
                          for status in labels)
        bar = self._proportion_bar(counts)
        self.spinner.report(f"  {bar}  {tally}" if bar else f"  {tally}")
        self.spinner.report(rule)

        return 0 if counts[CheckStatus.FAIL] == 0 else 1

    def run_all_checks(self) -> int:
        """Run all network checks"""
        environment = "コンテナ" if self.is_container else "ホスト"
        title = bold("ネットワーク診断", OUT)
        subtitle = paint16(f"{platform.system()} {platform.release()} · {platform.node()} · {environment}",
                           BRIGHT_BLACK, OUT)
        with self.spinner:
            self.spinner.report(f"{title}  {subtitle}")

            self.check_container_environment()
            self.check_network_interfaces()
            gateway = self.check_routing_table()
            dns_servers = self.check_dns_configuration()

            self.check_ping_localhost()
            self.check_ping_gateway(gateway)
            self.check_ping_external()

            self.check_dns_resolution(dns_servers)
            self.check_http_connectivity()

            self.check_ipv6()
            self.check_docker_specific()
            self.check_firewall()

            return self.print_summary()


def parsearg() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Network diagnostic tool for macOS and Ubuntu",
        epilog="Checks network connectivity step by step"
    )
    parser.add_argument('--version', action='version', version='%(prog)s 2.0')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Show detailed output for each check')
    parser.add_argument('--no-color', action='store_true',
                        help='Disable colored output (NO_COLOR and a non-terminal '
                             'destination are honored on their own)')
    return parser.parse_args()


def main() -> None:
    """Main function"""
    args = parsearg()

    set_color_mode("never" if args.no_color else "auto")
    checker = NetworkChecker(verbose=args.verbose)
    sys.exit(checker.run_all_checks())


if __name__ == '__main__':
    main()
