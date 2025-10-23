# Network Statistics

| Task | Linux | macOS | Windows |
|------|-------|-------|---------|
| Protocol statistics | `netstat -s`, `ss -s` | `netstat -s` | `netstat -s` |
| All connections | `netstat -an`, `ss -tan` | `netstat -an` | `netstat -an` |
| Established connections | `ss -tan state established` | `netstat -an \| grep ESTABLISHED` | `netstat -an \| findstr ESTABLISHED` |
| With process info | `ss -tanp`, `netstat -tanp` | `sudo lsof -i -P -n` | `netstat -ano`, `Get-NetTCPConnection` (PS) |
| Bandwidth monitor | `iftop`, `nethogs`, `vnstat`, `bmon` | `nettop` | `Get-NetAdapterStatistics` (PS) |
