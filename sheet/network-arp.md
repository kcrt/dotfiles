# ARP

| Task | Linux | macOS | Windows |
|------|-------|-------|---------|
| Show ARP cache | `ip neigh`, `arp -a` | `arp -a` | `arp -a` |
| Add ARP entry | `sudo ip neigh add 192.168.1.100 lladdr 00:11:22:33:44:55 dev eth0` | `sudo arp -s 192.168.1.100 00:11:22:33:44:55` | `arp -s 192.168.1.100 00-11-22-33-44-55` |
| Delete ARP entry | `sudo ip neigh del 192.168.1.100 dev eth0` | `sudo arp -d 192.168.1.100` | `arp -d 192.168.1.100` |
| Flush ARP cache | `sudo ip neigh flush all` | `sudo arp -a -d` | `netsh interface ip delete arpcache` |
