# WiFi

| Task | Linux (NetworkManager) | macOS | Windows |
|------|------------------------|-------|---------|
| List WiFi networks | `nmcli dev wifi list`, `iw dev wlan0 scan` | `airport -s` (see note) | `netsh wlan show networks` |
| Show connection info | `nmcli dev wifi`, `iwconfig wlan0` | `airport -I`, `networksetup -getairportnetwork en0` | `netsh wlan show interfaces` |
| Connect to network | `nmcli dev wifi connect SSID password PASSWORD` | `networksetup -setairportnetwork en0 SSID PASSWORD` | `netsh wlan connect name="SSID"` |
| Disconnect | `nmcli dev disconnect wlan0` | `sudo airport -z` | `netsh wlan disconnect` |
| Show saved profiles | `nmcli con show` | `networksetup -listpreferredwirelessnetworks en0` | `netsh wlan show profiles` |
| WiFi on/off | `nmcli radio wifi off/on` | `networksetup -setairportpower en0 off/on` | `netsh interface set interface "Wi-Fi" disabled/enabled` |

## macOS airport utility

Full path to airport utility:

```bash
/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport
```
