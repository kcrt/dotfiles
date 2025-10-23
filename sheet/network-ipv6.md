# IPv6

| Task | Linux | macOS | Windows |
|------|-------|-------|---------|
| Show IPv6 addresses | `ip -6 addr` | `ifconfig \| grep inet6` | `netsh interface ipv6 show address` |
| Show IPv6 routes | `ip -6 route` | `netstat -rn -f inet6` | `route print -6` |
| Add IPv6 address | `sudo ip -6 addr add 2001:db8::1/64 dev eth0` | `sudo ifconfig en0 inet6 2001:db8::1 prefixlen 64` | `netsh interface ipv6 set address "Ethernet" 2001:db8::1` |
| Enable IPv6 | `sudo sysctl -w net.ipv6.conf.all.disable_ipv6=0` | - | `netsh interface ipv6 set state enabled` |
| Disable IPv6 | `sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1` | `networksetup -setv6off Wi-Fi` | `netsh interface ipv6 set state disabled` |
| Force IPv6 ping | `ping -6 example.com` | `ping6 example.com` | `ping -6 example.com` |
