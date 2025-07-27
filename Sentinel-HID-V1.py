import pyudev
import subprocess
import time
import threading
import os
import json
import requests
from datetime import datetime
from evdev import InputDevice, categorize, ecodes

CONFIG_FILE = "config.json"
LOG_FILE = "log.txt"
WHITELIST_FILE = "whitelist.json"

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
        return {"bot_token": "", "chat_id": ""}

def load_whitelist():
    try:
        with open(WHITELIST_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def is_device_whitelisted(vendor, product, serial, whitelist):
    for entry in whitelist:
        if entry["vendor"] == vendor and entry["product"] == product:
            if not entry.get("serial") or entry.get("serial") == serial:
                return True
    return False

def log_event(message):
    with open(LOG_FILE, "a") as f:
        f.write(f"[{datetime.now()}] {message}\n")

def send_telegram_alert(message, config):
    token = config.get("bot_token", "")
    chat_id = config.get("chat_id", "")
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": message}
    try:
        requests.post(url, data=data, timeout=5)
    except Exception as e:
        print(f"[!] Telegram Error: {e}")

def block_usb_device(device):
    try:
        dev_path = device.device_path
        remove_path = os.path.join("/sys", dev_path.lstrip("/"), "remove")
        if os.path.exists(remove_path):
            os.system(f'echo 1 | sudo tee {remove_path} > /dev/null')
            print("[!] Device removed.")
    except Exception as e:
        print(f"[!] Error removing device: {e}")

def find_event_device_for_usb(device):
    vendor = device.get("ID_VENDOR_ID")
    product = device.get("ID_MODEL_ID")

    try:
        with open("/proc/bus/input/devices") as f:
            content = f.read()
    except Exception:
        return None

    blocks = content.strip().split("\n\n")
    for block in blocks:
        lines = block.split("\n")
        handlers = ""
        matched = False
        for line in lines:
            if line.startswith("H: Handlers="):
                handlers = line
            if "Vendor=" in line and "Product=" in line:
                if vendor.lower() in line.lower() and product.lower() in line.lower():
                    matched = True
        if matched and "event" in handlers:
            parts = handlers.split()
            for part in parts:
                if part.startswith("event"):
                    return "/dev/input/" + part
    return None

def monitor_keystrokes(event_path, vendor, product, serial, config, pyudev_device):
    try:
        dev = InputDevice(event_path)
        threshold_speed = 12
        key_times = []

        print(f"[~] Monitoring typing speed on {event_path}")
        for event in dev.read_loop():
            if event.type == ecodes.EV_KEY:
                key_event = categorize(event)
                if key_event.keystate == key_event.key_down:
                    now = time.time()
                    key_times.append(now)
                    key_times = [t for t in key_times if now - t <= 1]
                    if len(key_times) > threshold_speed:
                        alert_msg = (f" HID Rapid Typing Detected!\n"
                                     f"Vendor: {vendor}\nProduct: {product}\nSerial: {serial}\n"
                                     f"Speed: {len(key_times)} keys/sec")
                        print(alert_msg)
                        send_telegram_alert(alert_msg, config)
                        log_event(alert_msg)
                        block_usb_device(pyudev_device)
                        break
    except Exception as e:
        print(f"[!] Error in keystroke monitoring: {e}")

def is_hid_device(device):
    driver = device.get("ID_USB_DRIVER", "").lower()
    interfaces = device.get("ID_USB_INTERFACES", "")
    return "hid" in driver or "0301" in interfaces or "03" in interfaces

def is_storage_device(device):
    driver = device.get("ID_USB_DRIVER", "").lower()
    interfaces = device.get("ID_USB_INTERFACES", "")
    return "usb-storage" in driver or interfaces.startswith("08")

def start_monitor():
    config = load_config()
    whitelist = load_whitelist()
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by("usb")

    print("[*] Sentinel-HID is running...")

    for device in iter(monitor.poll, None):
        if device.action == "add":
            vendor = device.get("ID_VENDOR_ID", "N/A")
            product = device.get("ID_MODEL_ID", "N/A")
            serial = device.get("ID_SERIAL_SHORT", "N/A")
            model = device.get("ID_MODEL", "Unknown")

            print(f"[+] Device connected: {model} | Vendor={vendor} | Product={product} | Serial={serial}")

            if is_device_whitelisted(vendor, product, serial, whitelist):
                print("[✓] Whitelisted HID device. Ignored.")
                log_event(f"Ignored Whitelisted Device: V={vendor}, P={product}, S={serial}")
                continue

            if is_hid_device(device):
                print("[-] HID device detected and not whitelisted. Starting keystroke monitoring.")
                event_path = find_event_device_for_usb(device)
                if event_path:
                    t = threading.Thread(target=monitor_keystrokes, args=(event_path, vendor, product, serial, config, device), daemon=True)
                    t.start()
                else:
                    print("[!] No event device found.")
            else:
                if is_storage_device(device):
                    log_event(f"USB‑Storage Connected: Model={model}, V={vendor}, P={product}, S={serial}")
                print("[✓] Non-HID device. Ignored.")

if __name__ == "__main__":
    start_monitor()

