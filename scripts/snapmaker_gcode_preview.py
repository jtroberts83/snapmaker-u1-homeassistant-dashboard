#!/usr/bin/env python3
"""Snapmaker U1 - draw preview pictures of the current print from its G-code.

Makes two pictures in /config/www (shown by the dashboards as /local/...):

  snapmaker_u1_model_angle.png   the whole model from a second angle (default: from the back-right)
  snapmaker_u1_progress.png      the model filling in layer by layer as the print progresses

How it works: it asks the printer (Moonraker) which file is printing and how far along it is,
downloads the G-code once, and draws the tool paths itself. Only the Python standard library is
needed, so it runs on Home Assistant without installing anything. The drawing is done in a
detached background process, so the Home Assistant action returns immediately.

Usage:   python3 snapmaker_gcode_preview.py <printer-ip> [options]
Options: --port 7125                     Moonraker port
         --model-yaw 145 --model-pitch 32        angle of the "model" picture (degrees)
         --progress-yaw -35 --progress-pitch 32  angle of the layer-by-layer picture
         --progress-hide-supports        leave support material out of the layer-by-layer picture
         --generic-colors                use the height gradient instead of the real filament colors
         --model-hide-supports           leave support material out of the second-angle picture
         --out /config/www               where the pictures are written
         --cache /config/.snapmaker_preview      where parsed G-code is cached
         --foreground                    do the work now and print what happens (for testing)

Angles: yaw 0 looks at the printer from the front, 90 from the left side, 180 from the back,
-90 from the right. Pitch is how high you look down from: 0 = level, 90 = straight down.
"""
import argparse
import bisect
import hashlib
import json
import math
import os
import pickle
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from array import array

SIZE = 560          # picture size in pixels (square)
SS = 2              # supersampling factor (smooth edges)
BG = (28, 28, 28)   # same as the dashboard card background (#1c1c1c)
GHOST = (62, 72, 90)
FOOT = (74, 84, 102)
GRADIENT = [(56, 189, 248), (167, 139, 250), (244, 114, 182)]
MAX_SEGS = 350000   # above this, every n-th layer is drawn to keep the picture fast
LOCK_SECONDS = 600


# ----------------------------------------------------------------------------- printer access
def http_get(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "snapmaker-preview"})
    return urllib.request.urlopen(req, timeout=timeout)


def get_json(url):
    with http_get(url) as resp:
        return json.loads(resp.read().decode("utf-8"))


def printer_state(base):
    data = get_json(base + "/printer/objects/query?print_stats&virtual_sdcard")
    status = data.get("result", {}).get("status", {})
    ps = status.get("print_stats", {}) or {}
    vs = status.get("virtual_sdcard", {}) or {}
    info = ps.get("info", {}) or {}
    return {
        "filename": ps.get("filename") or "",
        "state": ps.get("state") or "",
        "file_position": vs.get("file_position") or 0,
        "current_layer": info.get("current_layer"),
        "total_layer": info.get("total_layer"),
    }


def parse_hex(v):
    v = str(v or "").strip().lstrip("#")
    if len(v) in (6, 8):
        try:
            return usable((int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)))
        except ValueError:
            return None
    return None


def filament_colors(base, parsed):
    """{tool index: (r, g, b)} from the printer's filament settings, else from the G-code header."""
    found = {}
    try:
        data = get_json(base + "/printer/objects/query?print_task_config")
        cfg = data.get("result", {}).get("status", {}).get("print_task_config", {}) or {}
        for i, v in enumerate(cfg.get("filament_color_rgba") or []):
            c = parse_hex(v)
            if c:
                found[i] = c
    except Exception:
        pass
    for i, v in enumerate(parsed.get("header_colors") or []):
        if i not in found:
            c = parse_hex(v)
            if c:
                found[i] = c
    return found


def file_key(base, filename):
    try:
        meta = get_json(base + "/server/files/metadata?filename=" + urllib.parse.quote(filename))
        res = meta.get("result", {})
        return "%s|%s|%s" % (filename, res.get("size"), res.get("modified"))
    except Exception:
        return filename


def download(base, filename, dest):
    url = base + "/server/files/gcodes/" + urllib.parse.quote(filename)
    with http_get(url, timeout=60) as resp, open(dest, "wb") as out:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)


# ----------------------------------------------------------------------------- G-code parsing
def parse_gcode(path):
    """Return the extruding line segments of every layer."""
    x = y = z = e = 0.0
    abs_xyz = True
    abs_e = True
    layers = []      # one flat array('f') per layer: x0 y0 x1 y1 ...
    supports = []    # the same, for support material (slicers mark it with ";TYPE:Support")
    is_support = False
    tool = 0
    hdr_colors = None
    layer_z = []
    layer_off = []   # byte offset in the file where each layer starts
    curz = None
    offset = 0
    minx = miny = 1e9
    maxx = maxy = -1e9
    maxz = 0.0
    with open(path, "rb") as fh:
        for raw in fh:
            start = offset
            offset += len(raw)
            if not raw or raw[0] in (59, 10, 13):      # ';' or empty line
                if raw.startswith(b";TYPE:"):
                    is_support = b"support" in raw.lower()
                elif raw[:1] == b";" and b"filament_colo" in raw[:40].lower() and b"=" in raw:
                    hdr_colors = [c.strip().strip(b'"').decode("ascii", "ignore")
                                  for c in raw.split(b"=", 1)[1].replace(b",", b";").split(b";")]
                continue
            code = raw.split(b";", 1)[0].split()
            if not code:
                continue
            cmd = code[0].upper()
            if cmd[:1] == b"T" and cmd[1:].isdigit():
                tool = int(cmd[1:])
                continue
            if cmd in (b"G1", b"G0", b"G2", b"G3", b"G01", b"G00"):
                nx, ny, nz, ne = x, y, z, None
                for p in code[1:]:
                    c = p[:1].upper()
                    try:
                        v = float(p[1:])
                    except ValueError:
                        continue
                    if c == b"X":
                        nx = v if abs_xyz else x + v
                    elif c == b"Y":
                        ny = v if abs_xyz else y + v
                    elif c == b"Z":
                        nz = v if abs_xyz else z + v
                    elif c == b"E":
                        ne = v
                de = 0.0
                if ne is not None:
                    if abs_e:
                        de = ne - e
                        e = ne
                    else:
                        de = ne
                if de > 0 and (nx != x or ny != y):
                    if curz is None or abs(nz - curz) > 0.004:
                        layers.append(array("f"))
                        supports.append(array("f"))
                        layer_z.append(nz)
                        layer_off.append(start)
                        curz = nz
                    (supports if is_support else layers)[-1].extend((x, y, nx, ny, tool))
                    if x < minx: minx = x
                    if nx < minx: minx = nx
                    if y < miny: miny = y
                    if ny < miny: miny = ny
                    if x > maxx: maxx = x
                    if nx > maxx: maxx = nx
                    if y > maxy: maxy = y
                    if ny > maxy: maxy = ny
                    if nz > maxz: maxz = nz
                x, y, z = nx, ny, nz
            elif cmd == b"G90":
                abs_xyz = True
            elif cmd == b"G91":
                abs_xyz = False
            elif cmd == b"M82":
                abs_e = True
            elif cmd == b"M83":
                abs_e = False
            elif cmd == b"G92":
                for p in code[1:]:
                    if p[:1].upper() == b"E":
                        try:
                            e = float(p[1:])
                        except ValueError:
                            pass
    if not layers:
        raise ValueError("no extruding moves found in the G-code")
    return {"version": 3, "header_colors": hdr_colors, "layers": layers, "supports": supports, "layer_z": layer_z, "layer_off": layer_off,
            "bbox": (minx, miny, 0.0, maxx, maxy, maxz)}


# ----------------------------------------------------------------------------- tiny renderer
class Canvas:
    def __init__(self, size, ss):
        self.n = size * ss
        self.ss = ss
        self.size = size
        self.buf = bytearray(bytes(BG) * (self.n * self.n))

    def line(self, x0, y0, x1, y1, color):
        n = self.n
        buf = self.buf
        r, g, b = color
        x0 = int(x0); y0 = int(y0); x1 = int(x1); y1 = int(y1)
        if (x0 < 0 and x1 < 0) or (y0 < 0 and y1 < 0) or (x0 >= n - 1 and x1 >= n - 1) or (y0 >= n and y1 >= n):
            return
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            if 0 <= x0 < n - 1 and 0 <= y0 < n:
                i = (y0 * n + x0) * 3
                buf[i] = r; buf[i + 1] = g; buf[i + 2] = b
                buf[i + 3] = r; buf[i + 4] = g; buf[i + 5] = b      # 2 px wide at SS=2 -> ~1 px
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def to_png(self):
        n, ss, size, buf = self.n, self.ss, self.size, self.buf
        rows = []
        for oy in range(size):
            acc = [0] * (size * 3)
            for k in range(ss):
                row = buf[((oy * ss + k) * n) * 3:((oy * ss + k + 1) * n) * 3]
                for c in range(3):
                    chan = row[c::3]
                    for j in range(ss):
                        part = chan[j::ss]
                        base = c
                        for idx, val in enumerate(part):
                            acc[idx * 3 + base] += val
            div = ss * ss
            rows.append(b"\x00" + bytes(v // div for v in acc))
        raw = b"".join(rows)

        def chunk(tag, data):
            return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
        return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")


def lerp_color(t):
    t = max(0.0, min(1.0, t)) * (len(GRADIENT) - 1)
    i = min(int(t), len(GRADIENT) - 2)
    f = t - i
    a, b = GRADIENT[i], GRADIENT[i + 1]
    return tuple(int(a[k] + (b[k] - a[k]) * f) for k in range(3))


class Projector:
    def __init__(self, bbox, yaw, pitch, size_px):
        self.cy = math.cos(math.radians(yaw)); self.sy = math.sin(math.radians(yaw))
        self.cp = math.cos(math.radians(pitch)); self.sp = math.sin(math.radians(pitch))
        minx, miny, minz, maxx, maxy, maxz = bbox
        self.ox = (minx + maxx) / 2
        self.oy = (miny + maxy) / 2
        pts = [self._raw(x, y, z) for x in (minx, maxx) for y in (miny, maxy) for z in (minz, maxz)]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        w = max(xs) - min(xs) or 1.0
        h = max(ys) - min(ys) or 1.0
        margin = 0.09
        self.scale = size_px * (1 - 2 * margin) / max(w, h)
        self.cx = (max(xs) + min(xs)) / 2
        self.cyv = (max(ys) + min(ys)) / 2
        self.half = size_px / 2

    def _raw(self, x, y, z):
        x -= getattr(self, "ox", 0.0); y -= getattr(self, "oy", 0.0)
        xr = x * self.cy - y * self.sy
        yr = x * self.sy + y * self.cy
        return xr, z * self.cp + yr * self.sp

    def __call__(self, x, y, z):
        a, b = self._raw(x, y, z)
        return self.half + (a - self.cx) * self.scale, self.half - (b - self.cyv) * self.scale


def pick_layers(count, keep_last, max_segments, seg_total):
    """Return the layer indexes to draw (every n-th layer for very large files)."""
    stride = 1
    if seg_total > max_segments:
        stride = int(math.ceil(seg_total / float(max_segments)))
    idx = set(range(0, count, stride))
    idx.add(count - 1)
    if keep_last is not None and 0 <= keep_last < count:
        idx.add(keep_last)
    return idx


def tint(rgb, f):
    return tuple(max(0, min(255, int(c * f))) for c in rgb)


def usable(rgb):
    """Lift very dark filaments (black) so they stay visible on the dark background."""
    if max(rgb) < 90:
        return tuple(int(c * 0.5 + 70) for c in rgb)
    return rgb


def render(parsed, yaw, pitch, printed=None, hide_supports=False, tool_colors=None):
    """printed = number of layers already printed (None = draw everything as finished)."""
    layers, lz, bbox = parsed["layers"], parsed["layer_z"], parsed["bbox"]
    supports = parsed.get("supports") or [array("f")] * len(layers)
    canvas = Canvas(SIZE, SS)
    proj = Projector(bbox, yaw, pitch, canvas.n)
    # footprint of the model on the plate
    minx, miny, _, maxx, maxy, _ = bbox
    pad = 0.06 * max(maxx - minx, maxy - miny)
    corners = [(minx - pad, miny - pad), (maxx + pad, miny - pad), (maxx + pad, maxy + pad), (minx - pad, maxy + pad)]
    for i in range(4):
        a = proj(corners[i][0], corners[i][1], 0.0)
        b = proj(corners[(i + 1) % 4][0], corners[(i + 1) % 4][1], 0.0)
        canvas.line(a[0], a[1], b[0], b[1], FOOT)
    total = len(layers)
    seg_total = sum(len(l) // 5 for l in layers) + (0 if hide_supports else sum(len(l) // 5 for l in supports))
    last = None if printed is None else max(0, min(total, printed) - 1)
    draw = pick_layers(total, last, MAX_SEGS, seg_total)
    top = max(lz) or 1.0
    for li in range(total):
        if li not in draw:
            continue
        done = printed is None or li < printed
        glow = printed is not None and done and li >= printed - 2
        shade = 0.6 + 0.4 * (lz[li] / top)        # a little darker low down, for depth
        if done:
            grad = (250, 250, 250) if glow else lerp_color(lz[li] / top)
        else:
            grad = GHOST
        z = lz[li]
        for arr in ((layers[li],) if hide_supports else (supports[li], layers[li])):
            for k in range(0, len(arr), 5):
                if tool_colors and done:
                    base = tool_colors.get(int(arr[k + 4]), tool_colors.get(0))
                    color = grad if base is None else (
                        tuple((c + 255) // 2 for c in base) if glow else tint(base, shade))
                else:
                    color = grad
                x0, y0 = proj(arr[k], arr[k + 1], z)
                x1, y1 = proj(arr[k + 2], arr[k + 3], z)
                canvas.line(x0, y0, x1, y1, color)
    return canvas.to_png()


def write_png(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, path)


def placeholder_png(text_rows=3):
    c = Canvas(SIZE, SS)
    n = c.n
    for i in range(text_rows):                       # three soft bars: "preview on its way"
        w = n // 3 + i * n // 12
        y = n // 2 + (i - 1) * n // 14
        c.line(n // 2 - w // 2, y, n // 2 + w // 2, y, FOOT)
    return c.to_png()


# ----------------------------------------------------------------------------- main work
def work(args):
    base = "http://%s:%d" % (args.ip, args.port)
    out_model = os.path.join(args.out, "snapmaker_u1_model_angle.png")
    out_prog = os.path.join(args.out, "snapmaker_u1_progress.png")
    st = printer_state(base)
    filename = st["filename"]
    if not filename:
        log(args, "no file is loaded on the printer")
        return 0
    key = file_key(base, filename)
    os.makedirs(args.cache, exist_ok=True)
    cache_file = os.path.join(args.cache, hashlib.sha1(key.encode()).hexdigest() + ".pkl")
    marker = os.path.join(args.cache, "model_key.txt")
    parsed = None
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "rb") as fh:
                parsed = pickle.load(fh)
            if parsed.get("version") != 3:
                parsed = None
        except Exception:
            parsed = None
    if parsed is None:
        ph = placeholder_png()
        write_png(out_model, ph)
        write_png(out_prog, ph)
        tmp = os.path.join(args.cache, "download.gcode")
        t0 = time.time()
        download(base, filename, tmp)
        parsed = parse_gcode(tmp)
        os.remove(tmp)
        with open(cache_file, "wb") as fh:
            pickle.dump(parsed, fh, protocol=pickle.HIGHEST_PROTOCOL)
        for old in sorted((os.path.join(args.cache, f) for f in os.listdir(args.cache) if f.endswith(".pkl")),
                          key=os.path.getmtime)[:-3]:
            os.remove(old)
        log(args, "parsed %d layers in %.1fs" % (len(parsed["layers"]), time.time() - t0))
    total = len(parsed["layers"])
    colors = None if args.generic_colors else filament_colors(base, parsed)
    ckey = "gen" if not colors else ",".join("%d=%02x%02x%02x" % ((i,) + c) for i, c in sorted(colors.items()))
    # the whole model from the second angle: once per file
    done_key = open(marker).read() if os.path.exists(marker) else ""
    key = key + "|" + "%s,%s,%s,%s" % (args.model_yaw, args.model_pitch, args.model_hide_supports, ckey)
    if done_key != key:
        write_png(out_model, render(parsed, args.model_yaw, args.model_pitch, None, args.model_hide_supports, colors))
        with open(marker, "w") as fh:
            fh.write(key)
        log(args, "model picture written")
    # layer-by-layer picture
    if st["state"] == "complete":
        printed = total
    elif st["file_position"]:
        printed = bisect.bisect_right(parsed["layer_off"], st["file_position"])
    elif st["current_layer"]:
        printed = min(total, int(st["current_layer"]))
    else:
        printed = 0
    write_png(out_prog, render(parsed, args.progress_yaw, args.progress_pitch, printed, args.progress_hide_supports, colors))
    log(args, "progress picture written: %d of %d layers" % (printed, total))
    return 0


def log(args, msg):
    if args.foreground:
        print(msg)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ip")
    ap.add_argument("--port", type=int, default=7125)
    ap.add_argument("--model-yaw", type=float, default=145.0)
    ap.add_argument("--model-pitch", type=float, default=32.0)
    ap.add_argument("--progress-yaw", type=float, default=-35.0)
    ap.add_argument("--progress-pitch", type=float, default=32.0)
    ap.add_argument("--progress-hide-supports", action="store_true")
    ap.add_argument("--model-hide-supports", action="store_true")
    ap.add_argument("--generic-colors", action="store_true", help="use the height gradient instead of the filament colors")
    ap.add_argument("--out", default=os.environ.get("SNAPMAKER_PREVIEW_OUT", "/config/www"))
    ap.add_argument("--cache", default=os.environ.get("SNAPMAKER_PREVIEW_CACHE", "/config/.snapmaker_preview"))
    ap.add_argument("--foreground", action="store_true")
    ap.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.foreground or args.worker:
        lock = os.path.join(args.cache, "running.lock")
        try:
            os.makedirs(args.cache, exist_ok=True)
            return_code = work(args)
        except Exception as exc:  # noqa: BLE001
            print("preview failed: %s" % exc, file=sys.stderr)
            return_code = 1
        finally:
            try:
                os.remove(lock)
            except OSError:
                pass
        sys.exit(return_code)

    # normal call from Home Assistant: start a detached worker and return at once
    os.makedirs(args.cache, exist_ok=True)
    lock = os.path.join(args.cache, "running.lock")
    if os.path.exists(lock) and time.time() - os.path.getmtime(lock) < LOCK_SECONDS:
        print("a preview is already being drawn")
        return
    open(lock, "w").write(str(os.getpid()))
    cmd = [sys.executable, os.path.abspath(__file__)] + sys.argv[1:] + ["--worker"]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=open(os.path.join(args.cache, "last_error.log"), "w"),
                     stdin=subprocess.DEVNULL, start_new_session=True)
    print("preview started")


if __name__ == "__main__":
    main()
