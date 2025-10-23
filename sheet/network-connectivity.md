# Network Connectivity

| Task | Linux | macOS | Windows |
|------|-------|-------|---------|
| Ping host | `ping example.com` | `ping example.com` | `ping example.com` |
| Ping N times | `ping -c 4 example.com` | `ping -c 4 example.com` | `ping -n 4 example.com` |
| Ping with interval | `ping -i 2 example.com` | `ping -i 2 example.com` | - |
| Continuous ping | `ping example.com` (Ctrl+C to stop) | `ping example.com` | `ping -t example.com` |
| Ping IPv6 | `ping -6 example.com` | `ping6 example.com` | `ping -6 example.com` |
| Traceroute | `traceroute example.com` | `traceroute example.com` | `tracert example.com` |
| Traceroute (ICMP) | `traceroute -I example.com` | `traceroute -I example.com` | - |
| Traceroute (TCP) | `traceroute -T example.com` | - | - |
| Test TCP port | `nc -zv example.com 80`, `telnet example.com 80` | `nc -zv example.com 80`, `telnet example.com 80` | `telnet example.com 80`, `Test-NetConnection example.com -Port 80` (PS) |
| Test UDP port | `nc -zuv example.com 53` | `nc -zuv example.com 53` | - |