#!/usr/bin/env python3
"""Snapmaker U1 camera keep-alive.

The U1's camera only produces fresh pictures while something has asked it to "monitor".
This opens a WebSocket to the printer and calls the Moonraker method camera.start_monitor.
Plain Python standard library only, so it runs from a Home Assistant shell_command with no installs.

Usage:   python3 snapmaker_camera_pulse.py <printer-ip> [api-key] [--secret snapmaker_api_key_2]

The printer's API key (needed for the WebSocket) is read, in this order, from:
  1. the second command-line argument
  2. the environment variable SNAPMAKER_API_KEY
  3. a line   snapmaker_api_key: YOUR_KEY   in /config/secrets.yaml   (recommended)
     (a second printer uses  --secret snapmaker_api_key_2  and a line  snapmaker_api_key_2: ...)

Output: the printer's raw reply. Exit code 0 = connected, 1 = failure.
"""
import base64
import json
import os
import re
import socket
import sys
import time


def parse_args():
    args = list(sys.argv[1:])
    secret = "snapmaker_api_key"
    if "--secret" in args:
        i = args.index("--secret")
        secret = args[i + 1] if i + 1 < len(args) else secret
        del args[i:i + 2]
    return args, secret


ARGS, SECRET = parse_args()


def get_api_key() -> str:
    if len(ARGS) > 1 and ARGS[1]:
        return ARGS[1]
    if os.environ.get("SNAPMAKER_API_KEY"):
        return os.environ["SNAPMAKER_API_KEY"]
    for path in ("/config/secrets.yaml", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "secrets.yaml")):
        try:
            with open(path, encoding="utf-8") as fh:
                match = re.search(r"^" + re.escape(SECRET) + r":\s*['\"]?([^'\"\s#]+)", fh.read(), re.M)
            if match:
                return match.group(1)
        except OSError:
            continue
    return ""


def send_pulse(printer_ip: str, api_key: str) -> int:
    if not api_key:
        print("No API key found. Add  %s: <your key>  to /config/secrets.yaml" % SECRET, file=sys.stderr)
        return 1
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((printer_ip, 80))

        # Fresh WebSocket handshake
        ws_key = base64.b64encode(os.urandom(16)).decode("utf-8")
        handshake = (
            f"GET /websocket?token={api_key} HTTP/1.1\r\n"
            f"Host: {printer_ip}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {ws_key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        s.send(handshake.encode("utf-8"))

        response = s.recv(1024)
        if b"101" not in response:
            s.close()
            print("WebSocket handshake refused (check the printer IP and API key): "
                  + response.decode("utf-8", errors="ignore")[:200], file=sys.stderr)
            return 1

        def send_frame(payload_dict):
            payload = json.dumps(payload_dict, separators=(",", ":")).encode("utf-8")
            payload_len = len(payload)
            mask_key = b"\x11\x22\x33\x44"
            frame = bytearray([0x81])
            if payload_len <= 125:
                frame.append(payload_len | 0x80)
            else:
                frame.append(126 | 0x80)
                frame.extend(payload_len.to_bytes(2, byteorder="big"))
            frame.extend(mask_key)
            masked = bytearray(payload_len)
            for i in range(payload_len):
                masked[i] = payload[i] ^ mask_key[i % 4]
            frame.extend(masked)
            s.send(frame)

        send_frame({
            "jsonrpc": "2.0",
            "method": "camera.start_monitor",
            "params": {"domain": "lan", "interval": 0},
            "id": 1,
        })

        # Read briefly so the printer can process the command
        s.settimeout(1.0)
        raw_output = []
        start_time = time.time()
        while time.time() - start_time < 1.0:
            try:
                data = s.recv(4096)
                if not data:
                    break
                raw_output.append(data.decode("utf-8", errors="ignore"))
            except socket.timeout:
                break
        s.close()
        print("Raw Printer Output: " + "".join(raw_output))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Connection Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if not ARGS:
        sys.exit("Usage: snapmaker_camera_pulse.py <printer-ip> [api-key] [--secret snapmaker_api_key_2]")
    sys.exit(send_pulse(ARGS[0], get_api_key()))
