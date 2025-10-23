# Network Services Management

| Task | Linux (systemd) | macOS | Windows |
|------|-----------------|-------|---------|
| Restart network | `sudo systemctl restart NetworkManager` | - | `net stop/start "Windows Firewall"` |
| Network status | `systemctl status NetworkManager` | `networksetup -listallhardwareports` | `Get-NetAdapter` (PS) |
