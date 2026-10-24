#!/usr/bin/env python3
"""Fill in YOUR printer's details and write ready-to-use files to ./build/

Run it from the folder you downloaded:

    python3 customize.py

It asks six short questions, copies every YAML file into ./build/ with your values filled in,
and removes the optional pieces (email, phone push, speaker announcement) you leave blank.
Nothing is sent anywhere and your original files are never changed.

Prefer to do it by hand? Open each file in a text editor and use Find & Replace for these words
(INSTALL.md step 4 has the same table):

    YOURPRINTER           entity prefix of your Moonraker printer, e.g.  snapmaker_u1
    PRINTER_IP            e.g. 192.168.1.50
    YOUR_CAMERA_ENTITY_ID e.g. camera.snapmaker_u1_camera
    YOUR_PHONE_NOTIFY     e.g. notify.pixel_9            (optional)
    YOUR_EMAIL_NOTIFY     e.g. notify.my_gmail           (optional)
    YOUR_SPEAKER_NOTIFY   e.g. notify.living_room_tts    (optional)

Command-line use (no questions):
    python3 customize.py --prefix snapmaker_u1 --ip 192.168.1.50 --camera camera.snapmaker_u1_camera \\
        --phone notify.my_phone --email notify.my_gmail --speaker ""
"""
import argparse
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "build")
FILES = [
    "packages/snapmaker_u1.yaml",
    "scripts/snapmaker_camera_pulse.py",
    "scripts/snapmaker_gcode_preview.py",
    "automations/camera_keepalive.yaml",
    "automations/save_thumbnail.yaml",
    "automations/gcode_preview.yaml",
    "automations/print_finished.yaml",
    "automations/progress_emails.yaml",
    "dashboards/desktop.yaml",
    "dashboards/phone.yaml",
]


def ask(label, hint, default="", required=True):
    while True:
        suffix = f" [{default}]" if default else ""
        value = input(f"\n{label}\n  {hint}\n  > {suffix} ").strip()
        value = value or default
        if value or not required:
            return value
        print("  This one is required.")


def clean_prefix(value):
    """Accept 'snapmaker_u1', 'sensor.snapmaker_u1_current_print_state' or any entity of the printer."""
    value = value.strip().lower()
    if value.startswith("sensor."):
        value = value[len("sensor."):]
    for tail in ("_current_print_state", "_print_state", "_progress", "_filename"):
        if value.endswith(tail):
            value = value[: -len(tail)]
    return value


def second_printer(text, old, new):
    """Turn text written for printer 1 into text for printer 2.

    old / new are dicts with 'prefix', 'camera' and 'ip' (old = what the text contains now, e.g. the
    YOURPRINTER tokens; new = the real values for printer 2). Everything printer 2 owns gets a '2':
    helper sensors snapmaker_u1_2_*, picture files snapmaker_u1_2_*.png, shell commands *_2, the
    API key secret snapmaker_api_key_2, and automation names "Snapmaker U1 #2 - ...".
    """
    t = text
    for key, mark in (("camera", "@@CAM2@@"), ("ip", "@@IP2@@"), ("prefix", "@@PFX2@@")):
        t = t.replace(old[key], mark)
    t = t.replace('snapmaker_camera_pulse.py @@IP2@@"', 'snapmaker_camera_pulse.py @@IP2@@ --secret snapmaker_api_key_2"')
    t = t.replace('snapmaker_gcode_preview.py @@IP2@@"', 'snapmaker_gcode_preview.py @@IP2@@ --tag 2"')
    t = t.replace("send_snapmaker_pulse", "send_snapmaker_pulse_2")
    t = t.replace("shell_command.snapmaker_gcode_preview", "shell_command.snapmaker_gcode_preview_2")
    t = t.replace('  snapmaker_gcode_preview: "', '  snapmaker_gcode_preview_2: "')
    t = t.replace("packages/snapmaker_u1.yaml", "packages/snapmaker_u1_printer2.yaml")
    t = t.replace("Snapmaker U1 - ", "Snapmaker U1 #2 - ")
    t = re.sub(r"Snapmaker U1 (?!2 |#2 )", "Snapmaker U1 2 ", t)
    t = re.sub(r"(?<!notify\.)snapmaker_u1_(?!2_)", "snapmaker_u1_2_", t)
    for key, mark in (("camera", "@@CAM2@@"), ("ip", "@@IP2@@"), ("prefix", "@@PFX2@@")):
        t = t.replace(mark, new[key])
    return t


def two_view_dashboard(text, old, new):
    """Return the dashboard with a second view for printer 2 (a copy of view 1 with printer 2 values)."""
    head, body = text.split("\nviews:\n", 1)
    assert body.count("\n  - title:") == 0 and body.startswith("  - title:"), "expected exactly one view"
    first = body.replace("  - title: 3D Printer", "  - title: Printer 1", 1)
    second = second_printer(body, old, new)
    second = second.replace("  - title: 3D Printer", "  - title: Printer 2", 1).replace("    path: printer\n", "    path: printer2\n", 1)
    head = head.replace("\ntitle: Snapmaker U1", "\ntitle: Snapmaker U1", 1)
    note = "# Two printers: view 'Printer 1' and view 'Printer 2' (printer 2 uses the snapmaker_u1_2_* helper sensors).\n"
    return head.replace("\n\ntitle:", "\n" + note + "\ntitle:", 1) + "\nviews:\n" + first.rstrip("\n") + "\n" + second


def drop_block(text, name):
    return re.sub(rf"[ \t]*# BEGIN:{name}\n.*?[ \t]*# END:{name}\n\n?", "", text, flags=re.S)


def main():
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument("--prefix"); p.add_argument("--ip"); p.add_argument("--camera")
    p.add_argument("--phone"); p.add_argument("--email"); p.add_argument("--speaker")
    p.add_argument("--ip2", help="second printer: IP address"); p.add_argument("--prefix2", help="second printer: entity prefix")
    p.add_argument("--camera2", help="second printer: camera entity ID")
    a = p.parse_args()
    interactive = a.prefix is None

    if interactive:
        print("Snapmaker U1 dashboard - customize\n" + "=" * 36)
        print("Tip: in Home Assistant open Developer Tools -> States and search 'current_print_state'.")
        prefix = clean_prefix(ask("1/6  Printer entity prefix",
                                  "Paste the entity ID of your 'Current print state' sensor, e.g. sensor.snapmaker_u1_current_print_state"))
        ip = ask("2/6  Printer IP address", "e.g. 192.168.1.50")
        camera = ask("3/6  Camera entity ID", "The Generic Camera you create in INSTALL.md step 6", "camera.snapmaker_u1_camera")
        phone = ask("4/6  Phone notify entity (optional)", "e.g. notify.pixel_9 - press Enter to skip", required=False)
        email = ask("5/6  Email notify entity (optional)", "The SMTP recipient entity, e.g. notify.my_gmail - Enter to skip", required=False)
        speaker = ask("6/6  Speaker notify entity (optional)", "e.g. notify.living_room_announce - Enter to skip", required=False)
        second = None
        if input("\nDo you have a SECOND printer to add? (y/N) ").strip().lower().startswith("y"):
            p2 = clean_prefix(ask("2nd printer entity prefix", "Entity ID of its 'Current print state' sensor"))
            ip2 = ask("2nd printer IP address", "e.g. 192.168.1.51")
            cam2 = ask("2nd printer camera entity ID", "Its own Generic Camera", "camera.snapmaker_u1_camera_2")
            second = {"prefix": p2, "ip": ip2, "camera": cam2 if cam2.startswith("camera.") else "camera." + cam2}
    else:
        second = None
        if a.ip2 or a.prefix2:
            if not (a.ip2 and a.prefix2):
                sys.exit("For a second printer give both --ip2 and --prefix2 (and --camera2).")
            c2 = a.camera2 or "camera.snapmaker_u1_camera_2"
            second = {"prefix": clean_prefix(a.prefix2), "ip": a.ip2, "camera": c2 if c2.startswith("camera.") else "camera." + c2}
        prefix, ip = clean_prefix(a.prefix), a.ip or ""
        camera = a.camera or "camera.snapmaker_u1_camera"
        phone, email, speaker = a.phone or "", a.email or "", a.speaker or ""

    if not prefix or not ip:
        sys.exit("The printer prefix and IP address are required.")
    if not camera.startswith("camera."):
        camera = "camera." + camera
    for value, label in ((phone, "phone"), (email, "email"), (speaker, "speaker")):
        if value and not value.startswith("notify."):
            sys.exit(f"The {label} value should look like notify.something (got '{value}').")

    shutil.rmtree(OUT, ignore_errors=True)
    tokens = {"prefix": "YOURPRINTER", "camera": "YOUR_CAMERA_ENTITY_ID", "ip": "PRINTER_IP"}
    PER_PRINTER = {"packages/snapmaker_u1.yaml", "automations/camera_keepalive.yaml", "automations/save_thumbnail.yaml",
                   "automations/gcode_preview.yaml", "automations/print_finished.yaml", "automations/progress_emails.yaml"}
    for rel in FILES:
        if rel.endswith("progress_emails.yaml") and not email:
            continue
        src, dst = os.path.join(HERE, rel), os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        text = open(src, encoding="utf-8").read()
        for name, value in (("PHONE", phone), ("EMAIL", email), ("SPEAKER", speaker)):
            if not value:
                text = drop_block(text, name)
        def fill_in(t, cam, pfx, addr):
            for token, value in (("YOUR_CAMERA_ENTITY_ID", cam), ("YOUR_PHONE_NOTIFY", phone),
                                 ("YOUR_EMAIL_NOTIFY", email), ("YOUR_SPEAKER_NOTIFY", speaker),
                                 ("YOURPRINTER", pfx), ("PRINTER_IP", addr)):
                t = t.replace(token, value)
            return t
        if second and rel.startswith("dashboards/"):
            text = two_view_dashboard(text, tokens, second)
        if second and rel in PER_PRINTER:
            # printer 2 gets its own copy, with its own values already filled in
            t2 = second_printer(text, tokens, second)
            for token, value in (("YOUR_PHONE_NOTIFY", phone), ("YOUR_EMAIL_NOTIFY", email),
                                 ("YOUR_SPEAKER_NOTIFY", speaker)):
                t2 = t2.replace(token, value)
            with open(dst.replace(".yaml", "_printer2.yaml"), "w", encoding="utf-8") as fh:
                fh.write(t2)
        text = fill_in(text, camera, prefix, ip)
        open(dst, "w", encoding="utf-8").write(text)

    print("\nDone. Your customized files are in:", OUT)
    print("Copy them into Home Assistant exactly as INSTALL.md steps 5-9 describe.")
    if not email:
        print("(No email entity given, so the progress-email automation was skipped.)")


if __name__ == "__main__":
    main()
