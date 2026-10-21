#!/usr/bin/env python3
"""Snapmaker U1 camera keep-alive.

The U1's camera only produces fresh pictures while something has asked it to "monitor".
This asks the printer to start (or keep) its LAN camera monitor by calling the same
Moonraker method the Snapmaker app uses: camera.start_monitor.

Usage:   python3 snapmaker_camera_pulse.py <printer-ip> [port]
Output:  the printer's answer as JSON, e.g.
         {"state": "success", "url": "/files/camera/monitor.jpg"}

It only needs aiohttp, which is already part of Home Assistant, so it runs from a
shell_command with no extra install. Exit code 0 = success, 1 = failure.
"""
import asyncio
import json
import sys

import aiohttp

TIMEOUT = 10


async def pulse(host: str, port: int) -> int:
    url = f"ws://{host}:{port}/websocket"
    request = {
        "jsonrpc": "2.0",
        "method": "camera.start_monitor",
        "params": {"domain": "lan", "interval": 0},
        "id": 4242,
    }
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=TIMEOUT + 5)) as session:
            async with session.ws_connect(url, timeout=TIMEOUT) as ws:
                await ws.send_json(request)
                while True:
                    msg = await ws.receive(timeout=TIMEOUT)
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        print(json.dumps({"state": "error", "detail": f"unexpected websocket message {msg.type}"}))
                        return 1
                    data = json.loads(msg.data)
                    if data.get("id") != request["id"]:
                        continue  # notifications from Moonraker, keep waiting for our answer
                    if "error" in data:
                        print(json.dumps({"state": "error", "detail": data["error"]}))
                        return 1
                    print(json.dumps(data.get("result", data)))
                    return 0
    except Exception as err:  # noqa: BLE001 - report any failure to the log
        print(json.dumps({"state": "error", "detail": str(err)}))
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: snapmaker_camera_pulse.py <printer-ip> [port]", file=sys.stderr)
        sys.exit(2)
    sys.exit(asyncio.run(pulse(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 7125)))
