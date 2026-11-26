#!/usr/bin/env python3
"""Replay the native Film Shelf category regression on a disposable emulator."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--adb", default="adb")
    p.add_argument("--port", required=True, type=int)
    p.add_argument("--serial", required=True)
    p.add_argument("--apk-sha256", required=True)
    p.add_argument("--evidence", type=Path)
    args = p.parse_args()
    if not re.fullmatch(r"[0-9a-fA-F]{64}", args.apk_sha256):
        p.error("use the exact SHA-256 of the installed APK")
    prefix = [sys.executable, str(Path(__file__).with_name("android-device.py")),
              "--adb", args.adb, "--port", str(args.port), "--serial", args.serial]
    failures = []

    def call(*parts):
        result = subprocess.run(prefix + [str(v) for v in parts], capture_output=True, text=True, timeout=65)
        if result.returncode != 0:
            raise RuntimeError(f"verified emulator bridge failed: {parts[0]}")
        return result.stdout.strip()

    def ui():
        return [json.loads(line) for line in call("ui").splitlines()]

    def bounds(node):
        return tuple(int(v) for v in re.findall(r"\d+", node.get("bounds") or ""))

    def wait_for(predicate, seconds=18):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            try:
                result = predicate(ui())
                if result:
                    return result
            except (ValueError, RuntimeError):
                pass
            time.sleep(.2)
        return None

    def node(nodes, text=None, rid=None, selected=False):
        return next((n for n in nodes if (text is None or n["text"] == text)
                     and (rid is None or (n["resource-id"] or "").endswith(":id/" + rid))
                     and (not selected or n["selected"] == "true")), None)

    def tap(n):
        if n is None:
            raise RuntimeError("required fixture control not visible")
        x1, y1, x2, y2 = bounds(n)
        if x1 >= x2 or y1 >= y2:
            raise RuntimeError("required fixture control had no hit area")
        call("tap", (x1+x2)//2, (y1+y2)//2)

    def report(label, passed):
        print(json.dumps({"step": label, "status": "pass" if passed else "fail"}), flush=True)
        if not passed:
            failures.append(label)

    def cards(nodes, label):
        return [(n["text"], bounds(n)[1]) for n in nodes
                if (n["resource-id"] or "").endswith(":id/name") and (n["text"] or "").startswith(label+" ")]

    def save(label):
        if args.evidence:
            args.evidence.mkdir(parents=True, exist_ok=True)
            call("screen", args.evidence / (label+".png"))

    device = json.loads(call("device"))
    observed = call("digest")
    if observed.lower() != args.apk_sha256.lower():
        raise RuntimeError("installed APK digest did not match the target")
    print(json.dumps({"device": device, "apk_sha256": observed}), flush=True)
    call("start")
    initial = wait_for(lambda ns: ns if node(ns, "Touch Browse Lab") and node(ns, "Ember Shelf") else None, 30)
    if not initial:
        raise RuntimeError("the expected loopback browse fixture is not visible; no touch attempted")
    tap(node(initial, "Ember Shelf"))
    first = wait_for(lambda ns: ns if cards(ns,"Ember") and node(ns, "Harbor Shelf") else None, 28)
    report("one tap opens first category with fixture cards", bool(first))
    if not first:
        return 1
    shell = node(first, rid="filmCategoryBack")
    report("category uses the Film Shelf native shell", bool(shell))
    save("category-start")
    frame = node(first, rid="pager")
    if not frame:
        raise RuntimeError("category viewport not visible")
    x1,y1,x2,y2 = bounds(frame)
    x=(x1+x2)//2
    def yy(frac):
        return round(y1+(y2-y1)*frac)
    start = cards(first,"Ember")
    previous = start
    movers = 0
    for _ in range(3):
        call("swipe", x, yy(.88), x, yy(.34), 650)
        a=wait_for(lambda ns: cards(ns, "Ember"))
        time.sleep(.65)
        b=wait_for(lambda ns: cards(ns, "Ember"))
        if a and a==b and b!=previous and b!=start:
            movers+=1
        if b:
            previous=b
    report("consecutive swipes retain different settled rows", movers>=2 and previous!=start)
    call("swipe", x, yy(.44), x, yy(.70), 550)
    a=wait_for(lambda ns: cards(ns, "Ember"))
    time.sleep(.7)
    b=wait_for(lambda ns: cards(ns, "Ember"))
    report("mid-list reverse swipe does not refresh or jump to start", bool(a and a==b and b!=previous and b!=start))
    save("category-mid-list")
    tap(wait_for(lambda ns: node(ns, "Harbor Shelf")))
    harbor=wait_for(lambda ns: ns if cards(ns,"Harbor") and node(ns,"Harbor Shelf",selected=True) else None, 16)
    report("second tab switches the catalog on one tap", bool(harbor))
    if harbor:
        report("switching tabs does not open its filter", node(harbor,"Quiet Only") is None)
        tap(node(harbor,"Harbor Shelf"))
        opt=wait_for(lambda ns: node(ns,"Quiet Only"),15)
        report("tap on active tab opens its filter", bool(opt))
        if opt:
            tap(opt)
            report("one tap applies filter in the active category",
                   bool(wait_for(lambda ns: cards(ns, "Quiet Harbor"), 25)))
            call("key","BACK")
            wait_for(lambda ns: ns if not node(ns,"Quiet Only") and cards(ns, "Quiet Harbor") else None, 12)
        back=wait_for(lambda ns: node(ns,rid="filmCategoryBack"),8)
        if back:
            tap(back)
            report("on-screen Back returns to recommendations",
                   bool(wait_for(lambda ns: node(ns,"Touch Browse Lab"),15)))
    return int(bool(failures))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        print(json.dumps({"status":"blocked", "reason":str(e)}), flush=True)
        sys.exit(2)
