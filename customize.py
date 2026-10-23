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


def drop_block(text, name):
    return re.sub(rf"[ \t]*# BEGIN:{name}\n.*?[ \t]*# END:{name}\n\n?", "", text, flags=re.S)


def main():
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument("--prefix"); p.add_argument("--ip"); p.add_argument("--camera")
    p.add_argument("--phone"); p.add_argument("--email"); p.add_argument("--speaker")
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
    else:
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
    for rel in FILES:
        if rel.endswith("progress_emails.yaml") and not email:
            continue
        src, dst = os.path.join(HERE, rel), os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        text = open(src, encoding="utf-8").read()
        for name, value in (("PHONE", phone), ("EMAIL", email), ("SPEAKER", speaker)):
            if not value:
                text = drop_block(text, name)
        for token, value in (("YOUR_CAMERA_ENTITY_ID", camera), ("YOUR_PHONE_NOTIFY", phone),
                             ("YOUR_EMAIL_NOTIFY", email), ("YOUR_SPEAKER_NOTIFY", speaker),
                             ("YOURPRINTER", prefix), ("PRINTER_IP", ip)):
            text = text.replace(token, value)
        text = text.replace("media-source://camera/camera.", "media-source://camera/camera.")  # no-op, keeps ids intact
        open(dst, "w", encoding="utf-8").write(text)

    print("\nDone. Your customized files are in:", OUT)
    print("Copy them into Home Assistant exactly as INSTALL.md steps 5-9 describe.")
    if not email:
        print("(No email entity given, so the progress-email automation was skipped.)")


if __name__ == "__main__":
    main()
