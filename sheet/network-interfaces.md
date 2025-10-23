# Network Interface Information

| Task | Linux | macOS | Windows |
|------|-------|-------|---------|
| Show all interfaces | `ip addr`, `ip a` | `ifconfig` | `ipconfig` |
| Show detailed info | `ip addr show` | `ifconfig -a` | `ipconfig /all` |
| Show specific interface | `ip addr show dev eth0` | `ifconfig en0` | `ipconfig` (shows all) |
| Show only IPv4 | `ip -4 addr` | `ifconfig \| grep inet` | - |
| Show only IPv6 | `ip -6 addr` | `ifconfig \| grep inet6` | `ipconfig` (included) |
| Enable interface | `sudo ip link set eth0 up` | `sudo ifconfig en0 up` | `netsh interface set interface "Ethernet" enabled` |
| Disable interface | `sudo ip link set eth0 down` | `sudo ifconfig en0 down` | `netsh interface set interface "Ethernet" disabled` |
| Set IP address | `sudo ip addr add 192.168.1.100/24 dev eth0` | `sudo ifconfig en0 192.168.1.100 netmask 255.255.255.0` | `netsh interface ip set address "Ethernet" static 192.168.1.100 255.255.255.0 192.168.1.1` |
| Remove IP address | `sudo ip addr del 192.168.1.100/24 dev eth0` | `sudo ifconfig en0 delete 192.168.1.100` | - |
