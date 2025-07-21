# Sentinel-HID v1

Sentinel-HID is a lightweight and efficient Linux-based system designed to detect and alert the user whenever a USB Human Interface Device (HID) — such as a keyboard or mouse — is connected. Its primary use case is to prevent BadUSB attacks by identifying suspicious input devices.

## Features

- Monitors and logs all USB devices, including HID and storage class devices.
- Supports device whitelisting based on `vendor`, `product`, and optionally `serial`.
- Sends Telegram alerts when unknown or suspicious devices are connected.
- Designed to run as a background service using `systemd`.

## Setup

```bash
git clone https://github.com/CyberX-sec/Sentinel-HID.git
cd Sentinel-HID
sudo python3 Sentinel-HID-V1.py
```

## Configuration

- Edit `config.json` to add your Telegram bot token and chat ID:
```json
{
  "bot_token": "XXXX",
  "chat_id": "YYYY"
}
```

- Edit `whitelist.json` to include trusted devices:
```json
[
  {
    "vendor": "XXXX",
    "product": "YYYY",
    "serial": "optional"
  }
]
```

## Logs

All device events are logged in `log.txt`.


## BY

**Ehab Thaer-CyberX** 
