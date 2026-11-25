#!/usr/bin/env python3
"""Run on a disposable local Film Shelf emulator; export only fixed observations."""
import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

PACKAGE = "io.github.sekaikunkun.filmshelf"
MAX_CAPTURE = 1_048_576
AUTH_DIALOG = {"等待扫码登录", "完成登录后，选择重试播放。等待期间不会自动换线。", "继续等待", "重试播放"}
LEGACY_AUTH_DIALOG = {"需要扫码或登录", "完成验证后，选择重试播放。", "继续等待", "重试播放"}
SCENARIOS = ("playback", "login_wait")
# The user selects a numeric label unrelated to the source name or URL.
SOURCE_LABELS = ("A", "B", "C", "D", "E", "F", "G", "H")


class InvalidInput(Exception):
    pass


class CaptureError(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise InvalidInput


def capture(command, env):
    # Never inherit stderr or include the command, output, or exception in a report.
    # Read one bounded snapshot into memory, never a host file.
    with subprocess.Popen(command, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, start_new_session=True) as child:
        def stop(signum, frame):
            raise CaptureError
        old = signal.signal(signal.SIGALRM, stop)
        signal.alarm(12)
        try:
            data = child.stdout.read(MAX_CAPTURE + 1)
            if len(data) > MAX_CAPTURE or child.wait() != 0:
                raise CaptureError
            return data
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)
            if child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait()


def decode_snapshot(data):
    if b"<!" in data:
        raise CaptureError
    root = ET.fromstring(data)
    if root.tag != "hierarchy":
        raise CaptureError
    texts = set()
    for node in root.iter("node"):
        if node.get("package") != PACKAGE:
            continue
        resource = node.get("resource-id", "").rsplit("/", 1)[-1]
        value = node.get("text", "")
        if (value in AUTH_DIALOG or value in LEGACY_AUTH_DIALOG) and resource in {"alertTitle", "message", "button1", "button2"}:
            texts.add(value)
    return texts in (AUTH_DIALOG, LEGACY_AUTH_DIALOG)


SESSION = re.compile(
    r"^ {4}[^\n]+ \(userId=\d+\)\n"
    r" {6}ownerPid=\d+, ownerUid=\d+, userId=\d+\n"
    r" {6}package=[^\n]+\n"
    r"(?: {6}(?:launchIntent|mediaButtonReceiver)=[^\n]*\n)*"
    r" {6}active=true\n"
    r"(?: {6}(?:flags=|rating type=|controllers:)[^\n]*\n)*"
    r" {6}state=PlaybackState \{state=(PLAYING\(3\)|PAUSED\(2\)), position=(\d{1,14}), "
    r"buffered position=-?\d+, speed=(-?\d+(?:\.\d+)?), updated=(\d{1,16}),",
    re.MULTILINE,
)


def media_position(raw):
    rows = []
    for match in SESSION.finditer(raw.decode()):
        lines = match.group().splitlines()
        if lines[2] != "      package=" + PACKAGE:
            continue
        state, position, speed, updated = match.groups()
        if (state == "PLAYING(3)" and 0 < float(speed) <= 4) or (state == "PAUSED(2)" and float(speed) == 0):
            rows.append((tuple(lines[:2]), state, int(position), int(updated)))
    return rows[0] if len(rows) == 1 else None


def playback_progress(first, second):
    if first is None or second is None or first[:2] != second[:2]:
        return None
    _, state, pos1, time1 = first
    _, _, pos2, time2 = second
    if state == "PAUSED(2)":
        return False if pos1 == pos2 else None
    # Require new reported samples, not a clock extrapolated from a static
    # Android state. Reject regression, large jumps and stale updates.
    delta = pos2 - pos1
    elapsed = time2 - time1
    if delta == 0:
        return False
    if 0 < elapsed <= 10_000 and 0 < delta <= min(20_000, 4 * elapsed + 250):
        return True
    return None


def observe(args):
    adb = [args.adb, "-H", "127.0.0.1", "-P", str(args.port)]
    env = {k: v for k, v in os.environ.items() if k not in {
        "ADB_SERVER_SOCKET", "ANDROID_ADB_SERVER_PORT", "ANDROID_SERIAL"}}
    device = capture(adb + ["devices"], env).decode().splitlines()
    if not device or device[0] != "List of devices attached" or [
        row.split() for row in device[1:] if row.strip()
    ] != [[args.serial, "device"]]:
        raise CaptureError
    target = adb + ["-s", args.serial]
    if capture(target + ["shell", "getprop", "ro.kernel.qemu"], env).strip() != b"1":
        raise CaptureError

    # uiautomator requires a file path. Use a unique emulator-only file, restrictive
    # permissions, cleanup even on normal shell errors, and no screenshots/logcat.
    dump = ("umask 077; f=$(mktemp /data/local/tmp/film-check.XXXXXX) || exit 1; "
            "trap 'rm -f \"$f\"' EXIT HUP INT TERM; "
            "timeout 9 uiautomator dump \"$f\" >/dev/null 2>&1 && cat \"$f\"")
    def snapshot():
        return decode_snapshot(capture(target + ["exec-out", dump], env))

    if args.scenario == "login_wait":
        first = snapshot()
        time.sleep(3)
        return ("requires_login" if first and snapshot() else "unconfirmed"), None

    def media():
        return media_position(capture(target + ["shell", "dumpsys", "media_session"], env))

    first = media()
    time.sleep(4)
    second = media()
    advanced = playback_progress(first, second)
    if advanced is True:
        return "pass", True
    if advanced is None and snapshot():
        return "requires_login", None
    return "unconfirmed", advanced


def run(argv):
    parser = Parser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--adb", default="adb", help="trusted local platform-tools binary")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--source", choices=SOURCE_LABELS, required=True)
    parser.add_argument("--scenario", choices=SCENARIOS, required=True)
    parser.add_argument("--selection-verified", action="store_true",
                        help="operator verified the active provider and episode in the local UI")
    try:
        args = parser.parse_args(argv)
        if not re.fullmatch(r"emulator-[0-9]{4,5}", args.serial) or not 1024 <= args.port <= 65535 or args.port == 5037:
            raise InvalidInput
    except InvalidInput:
        print('{"outcome":"invalid_input"}')
        return 2
    outcome, advanced = "unconfirmed", None
    # A reporting label is not source evidence. Do not sample an unverified
    # selection (such as a rejected switch that left the old source playing).
    if args.selection_verified:
        try:
            outcome, advanced = observe(args)
        except (CaptureError, OSError, UnicodeError, ValueError, ET.ParseError, KeyboardInterrupt):
            outcome, advanced = "capture_unavailable", None
    # No free text, UI selectors, positions, route labels, error details or durations.
    print(json.dumps({"source": args.source, "scenario": args.scenario,
                      "outcome": outcome, "progress_advanced": advanced},
                     separators=(",", ":")))
    return 2 if outcome == "capture_unavailable" else 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
