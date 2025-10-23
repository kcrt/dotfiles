# DNS

[← Back to Network Commands](network.md)

See also: [dns.md](dns.md) for detailed DNS commands.

| Task | Linux | macOS | Windows |
|------|-------|-------|---------|
| View DNS servers | `cat /etc/resolv.conf`, `systemd-resolve --status` | `scutil --dns`, `networksetup -getdnsservers Wi-Fi` | `ipconfig /all`, `netsh interface ip show dns` |
| DNS lookup | `nslookup example.com`, `dig example.com` | `nslookup example.com`, `dig example.com` | `nslookup example.com` |
| Reverse DNS lookup | `dig -x 192.168.1.1` | `dig -x 192.168.1.1` | `nslookup 192.168.1.1` |
| Query specific DNS server | `dig @8.8.8.8 example.com` | `dig @8.8.8.8 example.com` | `nslookup example.com 8.8.8.8` |
| Flush DNS cache | `sudo systemd-resolve --flush-caches` | `sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder` | `ipconfig /flushdns` |
| Show DNS cache | `sudo systemd-resolve --statistics` | - | `ipconfig /displaydns` |
| Set DNS server | Edit `/etc/resolv.conf` or `nmcli` | `sudo networksetup -setdnsservers Wi-Fi 8.8.8.8 1.1.1.1` | `netsh interface ip set dns "Ethernet" static 8.8.8.8` |

## mDNS (Multicast DNS)

| Task | Linux (Avahi) | macOS (Bonjour) | Windows |
|------|---------------|-----------------|---------|
| Browse services | `avahi-browse -a`, `avahi-browse -t _http._tcp` | `dns-sd -B _http._tcp` | - |
| Lookup service | `avahi-browse -r _http._tcp` | `dns-sd -L "Service Name" _http._tcp` | - |
| Resolve hostname | `avahi-resolve -n hostname.local` | `dns-sd -G v4 hostname.local` | - |
| Ping .local | `ping hostname.local` | `ping hostname.local` | `ping hostname.local` |
