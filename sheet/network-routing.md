# Routing

| Task | Linux | macOS | Windows |
|------|-------|-------|---------|
| Show routing table | `ip route`, `route -n` | `netstat -r`, `route -n get default` | `route print`, `netstat -r` |
| Show default gateway | `ip route \| grep default` | `route -n get default` | `ipconfig \| findstr Gateway` |
| Add route | `sudo ip route add 192.168.2.0/24 via 192.168.1.1` | `sudo route add -net 192.168.2.0/24 192.168.1.1` | `route add 192.168.2.0 mask 255.255.255.0 192.168.1.1` |
| Add route to interface | `sudo ip route add 192.168.15.0/24 dev ppp0` | `sudo route add -net 192.168.15.0/24 -interface ppp0` | `route add 192.168.15.0 mask 255.255.255.0 IF <interface_number>` |
| Delete route | `sudo ip route del 192.168.2.0/24` | `sudo route delete -net 192.168.2.0/24` | `route delete 192.168.2.0` |
| Add default gateway | `sudo ip route add default via 192.168.1.1` | `sudo route add default 192.168.1.1` | `route add 0.0.0.0 mask 0.0.0.0 192.168.1.1` |