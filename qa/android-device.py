#!/usr/bin/env python3
"""Minimal emulator bridge for the independent acceptance agent; no model or API key."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

PACKAGE = "io.github.sekaikunkun.filmshelf"
HOME_ACTIVITY = PACKAGE + "/com.fongmi.android.tv.ui.activity.HomeActivity"
KEYS = ("UP", "DOWN", "LEFT", "RIGHT", "CENTER", "BACK", "ENTER", "MENU",
        "MEDIA_PLAY_PAUSE", "MEDIA_PAUSE", "MEDIA_PLAY")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--port", type=int, required=True, help="dedicated loopback ADB server")
    parser.add_argument("--serial", required=True, help="explicit emulator serial")
    modes = parser.add_subparsers(dest="mode", required=True)
    modes.add_parser("device")
    modes.add_parser("start")
    modes.add_parser("digest", help="report the installed Film Shelf APK digest")
    modes.add_parser("ui")
    modes.add_parser("logs")
    key = modes.add_parser("key")
    key.add_argument("button", choices=KEYS)
    tap = modes.add_parser("tap", help="tap a verified emulator coordinate")
    for axis in ("x", "y"):
        tap.add_argument(axis, type=int)
    swipe = modes.add_parser("swipe", help="swipe on the verified emulator screen")
    for axis in ("x1", "y1", "x2", "y2", "duration_ms"):
        swipe.add_argument(axis, type=int)
    image = modes.add_parser("screen")
    image.add_argument("output", type=Path)
    install = modes.add_parser("install")
    install.add_argument("apk", type=Path)
    install.add_argument("--sha256", required=True, help="expected local build digest")
    args = parser.parse_args()
    if not re.fullmatch(r"emulator-[0-9]{4,5}", args.serial) or not 1024 <= args.port <= 65535 or args.port == 5037:
        parser.error("an explicit emulator serial and loopback server port are required")

    if args.mode in ("tap", "swipe"):
        points = (args.x, args.y) if args.mode == "tap" else (args.x1, args.y1, args.x2, args.y2)
        if any(not 0 <= n <= 8191 for n in points) or args.mode == "swipe" and not 100 <= args.duration_ms <= 3000:
            parser.error("coordinates must be between 0 and 8191; swipe duration 100 to 3000 ms")
    adb = [args.adb, "-H", "127.0.0.1", "-P", str(args.port)]
    env = {k: v for k, v in os.environ.items() if k not in {"ADB_SERVER_SOCKET", "ANDROID_ADB_SERVER_PORT", "ANDROID_SERIAL"}}

    def command(prefix, *parts):
        result = subprocess.run(prefix + list(parts), env=env, stdout=subprocess.PIPE, timeout=60)
        if result.returncode:
            raise SystemExit(result.stdout.decode(errors="replace").strip()
                             or f"Failed: {parts[0]} (exit {result.returncode})")
        return result.stdout

    devices = command(adb, "devices").decode().splitlines()[1:]
    if [line.split() for line in devices if line.strip()] != [[args.serial, "device"]]:
        raise SystemExit("Refusing an ADB server with no device, an unexpected device, or multiple targets")
    target = adb + ["-s", args.serial]

    def run(*parts):
        return command(target, *parts)

    def shell(*parts):
        return run("shell", *parts).decode().strip()

    if shell("getprop", "ro.kernel.qemu") != "1":
        raise SystemExit("The selected target did not identify itself as an emulator")
    if args.mode == "device":
        print(json.dumps({"serial": args.serial, "abi": shell("getprop", "ro.product.cpu.abi"),
                          "api": shell("getprop", "ro.build.version.sdk"),
                          "page_size": shell("getconf", "PAGE_SIZE")}))
    elif args.mode == "digest":
        installed = shell("pm", "path", PACKAGE).removeprefix("package:")
        if not installed.startswith("/data/app/") or not installed.endswith("/base.apk") or "\n" in installed:
            raise SystemExit("No unique installed Film Shelf base APK")
        print(shell("sha256sum", installed).split()[0])
    elif args.mode == "install":
        hasher = hashlib.sha256()
        with args.apk.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                hasher.update(block)
        digest = hasher.hexdigest()
        if digest != args.sha256.lower():
            raise SystemExit("Local APK SHA-256 did not match")
        # Only accept the clean Film Shelf build, not an arbitrary input package.
        aapt = Path(os.environ["ANDROID_HOME"]) / "build-tools" / "37.0.0" / "aapt"
        badging = command([str(aapt)], "dump", "badging", str(args.apk)).decode()
        if not badging.startswith("package: name='" + PACKAGE + "'"):
            raise SystemExit("Unexpected APK package ID")
        print(run("install", "-r", str(args.apk)).decode().strip())
        installed = shell("pm", "path", PACKAGE).removeprefix("package:")
        current = shell("sha256sum", installed).split()[0]
        if current != digest:
            raise SystemExit("Installed base APK SHA-256 did not match")
        print(current)
    elif args.mode == "start":
        print(shell("am", "start", "-W", "-n", HOME_ACTIVITY))
    elif args.mode == "ui":
        shell("uiautomator", "dump", "/data/local/tmp/film-shelf-qa.xml")
        tree = ET.fromstring(run("exec-out", "cat", "/data/local/tmp/film-shelf-qa.xml"))
        for node in tree.iter("node"):
            if node.get("package") != PACKAGE:
                continue
            fields = {k: node.get(k) for k in ("text", "content-desc", "resource-id", "bounds", "focused", "enabled", "selected")}
            if (fields["text"] or fields["content-desc"] or fields["focused"] == "true"
                    or (fields["resource-id"] or "").endswith(":id/pager")):
                print(json.dumps(fields, ensure_ascii=False))
    elif args.mode == "key":
        shell("input", "keyevent", "KEYCODE_DPAD_" + args.button if args.button in KEYS[:5]
              else "KEYCODE_" + args.button)
    elif args.mode == "tap":
        shell("input", "tap", str(args.x), str(args.y))
    elif args.mode == "swipe":
        shell("input", "swipe", *(str(v) for v in (*points, args.duration_ms)))
    elif args.mode == "screen":
        png = run("exec-out", "screencap", "-p")
        if not png.startswith(b"\x89PNG\r\n\x1a\n"):
            raise SystemExit("No PNG returned")
        with args.output.open("xb") as f:
            f.write(png)
    elif args.mode == "logs":
        pid = shell("pidof", PACKAGE).split()
        if len(pid) != 1 or not pid[0].isdigit():
            raise SystemExit("No unique Film Shelf process")
        sys.stdout.buffer.write(run("logcat", "-d", "-t", "300", "--pid=" + pid[0]))


if __name__ == "__main__":
    main()
