#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-

"""
Network Diagnostic Tool
Checks network connectivity step by step for macOS and Ubuntu
"""

import argparse
import subprocess
import socket
import platform
import sys
import re
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class Colors:
    """ANSI color codes"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class CheckStatus(Enum):
    """Status of each check"""
    PASS = "✓"
    FAIL = "✗"
    WARN = "⚠"
    SKIP = "○"

    def colored(self) -> str:
        """Return colored status symbol"""
        if self == CheckStatus.PASS:
            return f"{Colors.GREEN}{self.value}{Colors.RESET}"
        elif self == CheckStatus.FAIL:
            return f"{Colors.RED}{self.value}{Colors.RESET}"
        elif self == CheckStatus.WARN:
            return f"{Colors.YELLOW}{self.value}{Colors.RESET}"
        else:  # SKIP
            return f"{Colors.WHITE}{self.value}{Colors.RESET}"


@dataclass
class CheckResult:
    """Result of a single check"""
    name: str
    status: CheckStatus
    message: str
    details: Optional[str] = None


class NetworkChecker:
    """Main network diagnostic checker"""

    def __init__(self, verbose: bool = False, no_color: bool = False):
        self.verbose = verbose
        self.no_color = no_color
        self.results: List[CheckResult] = []
        self.is_macos = platform.system() == "Darwin"
        self.is_linux = platform.system() == "Linux"
        self.is_container = self._detect_container()

        # Test targets
        self.test_server = "www.kcrt.net"
        self.test_server_ip = "219.94.243.204"
        self.test_url = "https://profile.kcrt.net/"

    def _detect_container(self) -> bool:
        """Detect if running inside a container"""
        # Check for /.dockerenv
        try:
            import os
            if os.path.exists('/.dockerenv'):
                return True
        except (OSError, IOError):
            pass

        # Check /proc/1/cgroup
        try:
            with open('/proc/1/cgroup', 'r') as f:
                content = f.read()
                if 'docker' in content or 'containerd' in content:
                    return True
        except (OSError, IOError):
            pass

        return False

    def _run_command(self, cmd: List[str], timeout: int = 5) -> Tuple[int, str, str]:
        """Run a shell command and return (returncode, stdout, stderr)"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            return -1, "", str(e)

    def _add_result(self, name: str, status: CheckStatus, message: str, details: Optional[str] = None):
        """Add a check result"""
        self.results.append(CheckResult(name, status, message, details))

    def check_container_environment(self):
        """Check container environment"""
        print("\n=== Container Environment ===")

        if self.is_container:
            self._add_result("Container Detection", CheckStatus.WARN,
                           "Running inside a container",
                           "Some checks may have limited functionality")

            # Check network mode
            returncode, stdout, _ = self._run_command(['cat', '/proc/1/cgroup'])
            if returncode == 0:
                self._add_result("Container CGroup", CheckStatus.PASS,
                               "Container environment detected", stdout[:200] if self.verbose else None)
        else:
            self._add_result("Container Detection", CheckStatus.PASS,
                           "Running on host system")

    def check_network_interfaces(self):
        """Check network interface status"""
        print("\n=== Network Interfaces ===")

        if self.is_macos:
            returncode, stdout, _ = self._run_command(['ifconfig'])
        else:
            returncode, stdout, _ = self._run_command(['ip', 'addr', 'show'])

        if returncode == 0:
            # Count active interfaces
            if self.is_macos:
                interfaces = re.findall(r'^(\w+):', stdout, re.MULTILINE)
            else:
                interfaces = re.findall(r'^\d+: (\w+):', stdout, re.MULTILINE)

            active_count = len([i for i in interfaces if i != 'lo'])
            self._add_result("Network Interfaces", CheckStatus.PASS,
                           f"Found {active_count} active interface(s)",
                           stdout if self.verbose else None)

            # Check for link status
            if not self.is_macos:
                returncode, stdout, _ = self._run_command(['ip', '-s', 'link'])
                if returncode == 0 and self.verbose:
                    self._add_result("Interface Statistics", CheckStatus.PASS,
                                   "Retrieved interface statistics", stdout)
        else:
            self._add_result("Network Interfaces", CheckStatus.FAIL,
                           "Failed to get interface information")

    def check_routing_table(self) -> Optional[str]:
        """Check routing table and default gateway"""
        print("\n=== Routing Table ===")

        if self.is_macos:
            returncode, stdout, _ = self._run_command(['netstat', '-rn'])
            # Match: default gateway flags interface [extra]
            # Format: default  192.168.0.1  UGScg  en21
            # Capture gateway, flags, interface, and any remaining text (for '!' detection)
            default_route_pattern = r'^default\s+(\S+)\s+(\S+)\s+(\S+)(?:\s+(.+))?$'
        else:
            returncode, stdout, _ = self._run_command(['ip', 'route', 'show'])
            default_route_pattern = r'^default via (\S+)(?:\s+dev\s+(\S+))?'

        if returncode == 0:
            # Find all default gateways
            gateways = []

            # For macOS, only process IPv4 routes (stop at Internet6: section)
            lines = stdout.split('\n')

            for line in lines:
                # Stop processing at IPv6 section on macOS
                if self.is_macos and line.startswith('Internet6:'):
                    break

                if self.is_macos:
                    match = re.match(default_route_pattern, line)
                    if match:
                        gateway_addr = match.group(1)
                        interface = match.group(3)
                        rest = match.group(4) if match.group(4) else ""

                        # Skip if:
                        # - Gateway is a link address (starts with "link#")
                        # - Line ends with '!' (reject route)
                        # - Gateway is 0.0.0.0
                        if (gateway_addr.startswith('link#') or
                            '!' in rest or
                            gateway_addr == '0.0.0.0'):
                            continue

                        gateways.append((gateway_addr, interface))
                else:
                    # Linux
                    match = re.match(default_route_pattern, line)
                    if match:
                        gateway_addr = match.group(1)
                        interface = match.group(2) if match.group(2) else None

                        if gateway_addr != '0.0.0.0':
                            gateways.append((gateway_addr, interface))

            if len(gateways) == 0:
                self._add_result("Default Gateway", CheckStatus.FAIL,
                               "No valid default gateway found", stdout)
                return None
            elif len(gateways) == 1:
                gateway_addr, interface = gateways[0]
                interface_info = f" via {interface}" if interface else ""
                self._add_result("Default Gateway", CheckStatus.PASS,
                               f"Gateway found: {gateway_addr}{interface_info}",
                               stdout if self.verbose else None)
                return gateway_addr
            else:
                # Multiple default gateways detected
                gateway_list = [f"{gw}{f' via {iface}' if iface else ''}"
                              for gw, iface in gateways]
                self._add_result("Multiple Default Gateways", CheckStatus.WARN,
                               f"Found {len(gateways)} default gateways: {', '.join(gateway_list)}",
                               stdout if self.verbose else None)
                self._add_result("Gateway Warning", CheckStatus.WARN,
                               "Multiple default gateways may cause routing issues",
                               "This typically happens when both wired and wireless connections are active. "
                               "Consider disabling one interface or adjusting route metrics.")
                # Return the first gateway for ping tests
                return gateways[0][0]
        else:
            self._add_result("Default Gateway", CheckStatus.FAIL,
                           "Failed to get routing table")
            return None

    def check_dns_configuration(self):
        """Check DNS configuration"""
        print("\n=== DNS Configuration ===")

        dns_servers = []

        if self.is_macos:
            returncode, stdout, _ = self._run_command(['scutil', '--dns'])
            if returncode == 0:
                dns_servers = re.findall(r'nameserver\[\d+\] : (\S+)', stdout)
        else:
            try:
                with open('/etc/resolv.conf', 'r') as f:
                    content = f.read()
                    dns_servers = re.findall(r'nameserver\s+(\S+)', content)
                    if self.verbose:
                        self._add_result("DNS Config File", CheckStatus.PASS,
                                       "/etc/resolv.conf readable", content)
            except Exception as e:
                self._add_result("DNS Config File", CheckStatus.FAIL,
                               f"Failed to read /etc/resolv.conf: {e}")

        if dns_servers:
            self._add_result("DNS Servers", CheckStatus.PASS,
                           f"Found {len(dns_servers)} DNS server(s): {', '.join(dns_servers[:3])}")
            return dns_servers
        else:
            self._add_result("DNS Servers", CheckStatus.WARN,
                           "No DNS servers found")
            return []

    def check_ping_localhost(self):
        """Ping localhost"""
        print("\n=== Localhost Connectivity ===")

        ping_cmd = ['ping', '-c', '3', '127.0.0.1']
        if self.is_macos:
            ping_cmd = ['ping', '-c', '3', '127.0.0.1']

        returncode, stdout, _ = self._run_command(ping_cmd, timeout=10)

        if returncode == 0:
            self._add_result("Localhost Ping", CheckStatus.PASS,
                           "Localhost reachable",
                           stdout if self.verbose else None)
        else:
            self._add_result("Localhost Ping", CheckStatus.FAIL,
                           "Failed to ping localhost")

    def check_ping_gateway(self, gateway: Optional[str]):
        """Ping default gateway"""
        print("\n=== Gateway Connectivity ===")

        if not gateway:
            self._add_result("Gateway Ping", CheckStatus.FAIL,
                           "No gateway to test - cannot verify gateway connectivity")
            return

        ping_cmd = ['ping', '-c', '4', gateway]
        returncode, stdout, _ = self._run_command(ping_cmd, timeout=15)

        if returncode == 0:
            # Extract packet loss
            loss_match = re.search(r'(\d+)% packet loss', stdout)
            loss = loss_match.group(1) if loss_match else "unknown"

            # Extract average latency
            if self.is_macos:
                latency_match = re.search(r'min/avg/max/stddev = [\d.]+/([\d.]+)/', stdout)
            else:
                latency_match = re.search(r'rtt min/avg/max/mdev = [\d.]+/([\d.]+)/', stdout)

            avg_latency = latency_match.group(1) if latency_match else "unknown"

            self._add_result("Gateway Ping", CheckStatus.PASS,
                           f"Gateway reachable (loss: {loss}%, avg: {avg_latency}ms)",
                           stdout if self.verbose else None)
        else:
            self._add_result("Gateway Ping", CheckStatus.FAIL,
                           f"Failed to ping gateway {gateway}")

    def check_ping_external(self):
        """Ping external servers"""
        print("\n=== External Connectivity ===")

        # Test multiple external servers
        test_servers = [
            ("Google DNS", "8.8.8.8"),
            ("Cloudflare DNS", "1.1.1.1"),
            ("KCRT Server", self.test_server_ip),
        ]

        for name, ip in test_servers:
            ping_cmd = ['ping', '-c', '3', ip]
            returncode, stdout, _ = self._run_command(ping_cmd, timeout=10)

            if returncode == 0:
                loss_match = re.search(r'(\d+)% packet loss', stdout)
                loss = loss_match.group(1) if loss_match else "unknown"

                self._add_result(f"Ping {name}", CheckStatus.PASS,
                               f"{ip} reachable (loss: {loss}%)",
                               stdout if self.verbose else None)
            else:
                self._add_result(f"Ping {name}", CheckStatus.FAIL,
                               f"Failed to ping {ip}")

    def check_dns_resolution(self, dns_servers: List[str]):
        """Check DNS resolution"""
        print("\n=== DNS Resolution ===")

        test_domains = [
            ("Google", "google.com"),
            ("KCRT", self.test_server),
        ]

        for name, domain in test_domains:
            try:
                ip = socket.gethostbyname(domain)
                self._add_result(f"DNS Resolve {name}", CheckStatus.PASS,
                               f"{domain} -> {ip}")
            except socket.gaierror as e:
                self._add_result(f"DNS Resolve {name}", CheckStatus.FAIL,
                               f"Failed to resolve {domain}: {e}")

        # Test specific DNS servers
        for dns_server in dns_servers[:2]:  # Test first 2 DNS servers
            returncode, stdout, stderr = self._run_command(
                ['nslookup', 'google.com', dns_server], timeout=5
            )

            if returncode == 0 and 'Address:' in stdout:
                self._add_result(f"DNS Query via {dns_server}", CheckStatus.PASS,
                               "DNS query successful",
                               stdout if self.verbose else None)
            else:
                self._add_result(f"DNS Query via {dns_server}", CheckStatus.FAIL,
                               f"DNS query failed: {stderr}")

    def check_http_connectivity(self):
        """Check HTTP/HTTPS connectivity"""
        print("\n=== HTTP/HTTPS Connectivity ===")

        # Check if curl is available
        returncode, _, _ = self._run_command(['which', 'curl'])

        if returncode != 0:
            self._add_result("HTTP/HTTPS Test", CheckStatus.SKIP,
                           "curl not available")
            return

        # Test HTTPS connection
        returncode, stdout, stderr = self._run_command(
            ['curl', '-sS', '-o', '/dev/null', '-w',
             '%{http_code}|%{time_total}', '--max-time', '10',
             self.test_url], timeout=15
        )

        if returncode == 0:
            parts = stdout.split('|')
            if len(parts) == 2:
                status_code, time_total = parts
                if status_code.startswith('2') or status_code.startswith('3'):
                    self._add_result("HTTPS Connection", CheckStatus.PASS,
                                   f"Successfully connected to {self.test_url} "
                                   f"(HTTP {status_code}, {float(time_total):.2f}s)")
                else:
                    self._add_result("HTTPS Connection", CheckStatus.WARN,
                                   f"Connected but received HTTP {status_code}")
        else:
            self._add_result("HTTPS Connection", CheckStatus.FAIL,
                           f"Failed to connect to {self.test_url}: {stderr}")

        # Test with verbose TLS info
        if self.verbose:
            returncode, stdout, stderr = self._run_command(
                ['curl', '-v', '-o', '/dev/null', '--max-time', '10',
                 self.test_url], timeout=15
            )
            if returncode == 0:
                self._add_result("TLS Handshake", CheckStatus.PASS,
                               "TLS handshake successful", stderr)

    def check_ipv6(self):
        """Check IPv6 connectivity"""
        print("\n=== IPv6 Connectivity ===")

        if self.is_macos:
            returncode, stdout, _ = self._run_command(['ifconfig'])
            ipv6_pattern = r'inet6 ([\da-f:]+)'
        else:
            returncode, stdout, _ = self._run_command(['ip', '-6', 'addr', 'show'])
            ipv6_pattern = r'inet6 ([\da-f:]+)/\d+'

        if returncode == 0:
            ipv6_addrs = re.findall(ipv6_pattern, stdout)
            if ipv6_addrs:
                global_addrs = [addr for addr in ipv6_addrs
                              if not addr.startswith('fe80:') and addr != '::1']
                link_local = [addr for addr in ipv6_addrs if addr.startswith('fe80:')]

                if global_addrs:
                    self._add_result("IPv6 Global Address", CheckStatus.PASS,
                                   f"Found {len(global_addrs)} global IPv6 address(es)")
                else:
                    self._add_result("IPv6 Global Address", CheckStatus.WARN,
                                   "No global IPv6 address found")

                if link_local:
                    self._add_result("IPv6 Link-Local", CheckStatus.PASS,
                                   f"Found {len(link_local)} link-local address(es)")
            else:
                self._add_result("IPv6 Addresses", CheckStatus.WARN,
                               "No IPv6 addresses found")

        # Try IPv6 ping
        returncode, stdout, _ = self._run_command(['ping6', '-c', '2', 'google.com'], timeout=10)
        if returncode == 0:
            self._add_result("IPv6 Connectivity", CheckStatus.PASS,
                           "IPv6 connectivity working")
        else:
            self._add_result("IPv6 Connectivity", CheckStatus.WARN,
                           "IPv6 connectivity not available or not working")

    def check_docker_specific(self):
        """Docker-specific checks"""
        if not self.is_container:
            return

        print("\n=== Docker-Specific Checks ===")

        # Check Docker DNS
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)
            sock.connect(('127.0.0.11', 53))
            sock.close()
            self._add_result("Docker DNS Server", CheckStatus.PASS,
                           "Docker embedded DNS (127.0.0.11) accessible")
        except (OSError, socket.error):
            self._add_result("Docker DNS Server", CheckStatus.WARN,
                           "Docker embedded DNS not accessible")

        # Check container network namespace
        try:
            import os
            ns_link = os.readlink('/proc/self/ns/net')
            self._add_result("Network Namespace", CheckStatus.PASS,
                           f"Network namespace: {ns_link}")
        except (OSError, IOError):
            pass

    def check_firewall(self):
        """Check firewall status"""
        print("\n=== Firewall Status ===")

        if self.is_macos:
            returncode, stdout, _ = self._run_command(['sudo', '-n', 'pfctl', '-s', 'info'])
            if returncode == 0:
                if 'Status: Enabled' in stdout:
                    self._add_result("Firewall Status", CheckStatus.WARN,
                                   "macOS firewall is enabled",
                                   stdout if self.verbose else None)
                else:
                    self._add_result("Firewall Status", CheckStatus.PASS,
                                   "macOS firewall is disabled")
            else:
                self._add_result("Firewall Status", CheckStatus.SKIP,
                               "Cannot check firewall (need sudo)")
        else:
            # Check iptables
            returncode, stdout, _ = self._run_command(['sudo', '-n', 'iptables', '-L', '-n'])
            if returncode == 0:
                rules_count = len(stdout.split('\n'))
                self._add_result("Firewall Rules", CheckStatus.PASS,
                               f"iptables accessible ({rules_count} lines)",
                               stdout if self.verbose else None)
            else:
                self._add_result("Firewall Rules", CheckStatus.SKIP,
                               "Cannot check iptables (need sudo)")

    def print_summary(self):
        """Print summary of all checks"""
        print("\n" + "="*60)
        print("NETWORK DIAGNOSTIC SUMMARY")
        print("="*60)

        if self.is_container:
            print("Environment: Container")
        else:
            print(f"Environment: {platform.system()} {platform.release()}")

        print("\nResults:")
        print("-"*60)

        pass_count = 0
        fail_count = 0
        warn_count = 0
        skip_count = 0

        for result in self.results:
            if self.no_color:
                status_symbol = result.status.value
            else:
                status_symbol = result.status.colored()
            print(f"{status_symbol} {result.name}: {result.message}")

            if result.details and self.verbose:
                # Print first few lines of details
                detail_lines = result.details.split('\n')[:5]
                for line in detail_lines:
                    print(f"    {line}")
                if len(result.details.split('\n')) > 5:
                    print("    ...")

            if result.status == CheckStatus.PASS:
                pass_count += 1
            elif result.status == CheckStatus.FAIL:
                fail_count += 1
            elif result.status == CheckStatus.WARN:
                warn_count += 1
            elif result.status == CheckStatus.SKIP:
                skip_count += 1

        print("-"*60)
        print(f"Total: {len(self.results)} checks")

        if self.no_color:
            print(f"  Passed: {pass_count}")
            print(f"  Failed: {fail_count}")
            print(f"  Warnings: {warn_count}")
            print(f"  Skipped: {skip_count}")
        else:
            print(f"  {Colors.GREEN}Passed: {pass_count}{Colors.RESET}")
            print(f"  {Colors.RED}Failed: {fail_count}{Colors.RESET}")
            print(f"  {Colors.YELLOW}Warnings: {warn_count}{Colors.RESET}")
            print(f"  {Colors.WHITE}Skipped: {skip_count}{Colors.RESET}")
        print("="*60)

        # Return exit code based on failures
        return 0 if fail_count == 0 else 1

    def run_all_checks(self):
        """Run all network checks"""
        print("Starting Network Diagnostic Checks...")
        print(f"Platform: {platform.system()} {platform.release()}")

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
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Show detailed output for each check')
    parser.add_argument('--no-color', action='store_true',
                       help='Disable colored output')
    return parser.parse_args()


def main():
    """Main function"""
    args = parsearg()

    checker = NetworkChecker(verbose=args.verbose, no_color=args.no_color)
    exit_code = checker.run_all_checks()

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
