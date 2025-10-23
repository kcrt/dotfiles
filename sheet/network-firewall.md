# Firewall

## Basic Firewall Commands

| Task | Linux (iptables) | macOS (pf) | Windows |
|------|------------------|------------|---------|
| Show status | `sudo iptables -L` | `sudo pfctl -s rules` | `netsh advfirewall show allprofiles` |
| Enable firewall | - | `sudo pfctl -e` | `netsh advfirewall set allprofiles state on` |
| Disable firewall | - | `sudo pfctl -d` | `netsh advfirewall set allprofiles state off` |
| List rules | `sudo iptables -L -n -v` | `sudo pfctl -s rules` | `netsh advfirewall firewall show rule name=all`, `Get-NetFirewallRule` (PS) |
| Allow port | `sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT` | Edit `/etc/pf.conf` | `netsh advfirewall firewall add rule name="Allow 80" dir=in action=allow protocol=TCP localport=80` |

## Firewall (firewalld on Linux)

```bash
sudo firewall-cmd --list-all              # List all rules
sudo firewall-cmd --add-port=80/tcp --permanent
sudo firewall-cmd --reload
sudo firewall-cmd --remove-port=80/tcp --permanent
```
