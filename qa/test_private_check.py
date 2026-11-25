import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

SCRIPT = Path(__file__).with_name("private-check.py")
SPEC = importlib.util.spec_from_file_location("private_check", SCRIPT)
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)
MARKERS = ("URL_CANARY", "TOKEN_CANARY", "TITLE_CANARY", "QR_CANARY")
FAKE_ADB = """#!/usr/bin/env python3
import os, sys
from pathlib import Path
a = sys.argv[1:]
Path(__file__).with_name('adb-called').touch()
assert a[:4] == ['-H', '127.0.0.1', '-P', '15084']
assert not os.environ.get('ADB_SERVER_SOCKET')
print('URL_CANARY TOKEN_CANARY TITLE_CANARY QR_CANARY', file=sys.stderr)
if a[4:] == ['devices']:
    print('List of devices attached')
    print('emulator-5678\\tdevice')
    if os.environ['MODE'] == 'multiple':
        print('another-device\\tdevice')
elif a[4:] == ['-s','emulator-5678','shell','getprop','ro.kernel.qemu']:
    print('1')
elif a[4:7] == ['-s','emulator-5678','exec-out'] or a[4:] == ['-s','emulator-5678','shell','dumpsys','media_session']:
    if a[6] == 'exec-out':
        assert 'uiautomator dump' in a[7]
    assert all(x not in ' '.join(a) for x in ('screencap', 'logcat'))
    p = Path(__file__).with_name('next')
    if os.environ['MODE'] == 'timeout':
        import time
        sys.stdout.write('<hierarchy>QR_CANARY')
        sys.stdout.flush()
        time.sleep(30)
    elif os.environ['MODE'] == 'oversize':
        print('TITLE_CANARY' * 100000)
    elif os.environ['MODE'] == 'error':
        print('TOKEN_CANARY')
        sys.exit(1)
    else:
        print(p.with_suffix('.second' if p.exists() else '.first').read_text())
        p.touch()
else:
    sys.exit(99)
"""


def sample(login=False, lookalike=False):
    root = ET.Element("hierarchy")
    for field, canary in zip(("api", "token", "name", "code"), MARKERS):
        ET.SubElement(root, "node", package=CHECK.PACKAGE,
                      text="https://example.invalid/" + canary,
                      attrib={"resource-id": CHECK.PACKAGE + ":id/" + field,
                              "content-desc": canary})
    if login or lookalike:
        for rid, value in zip(("alertTitle", "message", "button2", "button1"),
                              ("等待扫码登录", "完成登录后，选择重试播放。等待期间不会自动换线。", "继续等待", "重试播放")):
            ET.SubElement(root, "node", package=CHECK.PACKAGE, text=value,
                          attrib={"resource-id": CHECK.PACKAGE + ":id/" + (rid if login else "name")})
    return ET.tostring(root, encoding="unicode")


def media(position, timestamp, state="PLAYING(3)", package=CHECK.PACKAGE, session=3):
    speed = "0.0" if state == "PAUSED(2)" else "1.0"
    return (
        f"    Media3 Lab/{session} (userId=0)\n"
        "      ownerPid=20, ownerUid=30, userId=0\n"
        f"      package={package}\n"
        "      launchIntent=null\n"
        "      mediaButtonReceiver=null\n"
        "      active=true\n"
        "      flags=7\n"
        "      rating type=0\n"
        "      controllers: 3\n"
        f"      state=PlaybackState {{state={state}, position={position}, "
        f"buffered position=50000, speed={speed}, updated={timestamp}, actions=123}}\n"
        "      metadata: size=5, description=TITLE_CANARY URL_CANARY TOKEN_CANARY QR_CANARY\n"
    )


class PrivateCheckTest(unittest.TestCase):
    def invoke(self, one="", two="", scenario="playback", mode="ok", source="A", verified=True):
        with tempfile.TemporaryDirectory() as scratch:
            adb = Path(scratch) / "adb"
            adb.write_text(FAKE_ADB)
            adb.chmod(0o700)
            for suffix, payload in ((".first", one), (".second", two)):
                adb.with_name("next").with_suffix(suffix).write_text(payload, encoding="utf-8")
            result = subprocess.run([sys.executable, str(SCRIPT), "--adb", str(adb),
                                     "--port", "15084", "--serial", "emulator-5678",
                                     "--source", source, "--scenario", scenario]
                                    + (["--selection-verified"] if verified else []),
                                    env=dict(os.environ, MODE=mode, ADB_SERVER_SOCKET="don't forward"),
                                    capture_output=True, text=True, timeout=16)
            if not verified:
                self.assertFalse(adb.with_name("adb-called").exists())
            self.assertEqual(result.stderr, "")
            for canary in MARKERS:
                self.assertNotIn(canary, result.stdout + result.stderr)
            self.assertEqual(len(result.stdout.splitlines()), 1)
            return result.returncode, json.loads(result.stdout)

    def test_playback_and_login_path_emit_only_fixed_report(self):
        for one, two, scenario, expected, progress in (
            (media(5_000, 52_000), media(8_000, 55_000), "playback", "pass", True),
            (media(5_000, 52_000, "PAUSED(2)"), media(5_000, 52_000, "PAUSED(2)"), "playback", "unconfirmed", False),
            (sample(login=True), sample(login=True), "login_wait", "requires_login", None),
            (sample(lookalike=True), sample(login=True), "login_wait", "unconfirmed", None),
        ):
            with self.subTest(scenario=scenario, expected=expected):
                code, report = self.invoke(one, two, scenario)
                self.assertEqual(code, 0)
                self.assertEqual(report, {"source": "A", "scenario": scenario, "outcome": expected,
                                          "progress_advanced": progress})

    def test_rejected_switch_cannot_credit_prior_playback_to_new_alias(self):
        prior = (media(5_000, 52_000), media(8_000, 55_000))
        self.assertEqual(self.invoke(*prior, source="B", verified=False),
                         (0, {"source": "B", "scenario": "playback",
                              "outcome": "unconfirmed", "progress_advanced": None}))
        self.assertEqual(self.invoke(sample(login=True), sample(login=True),
                                     scenario="login_wait", source="B", verified=False),
                         (0, {"source": "B", "scenario": "login_wait",
                              "outcome": "unconfirmed", "progress_advanced": None}))

    def test_errors_and_timeout_never_echo_raw_capture(self):
        for mode in ("error", "oversize", "multiple", "timeout", "ok"):
            with self.subTest(mode=mode):
                code, report = self.invoke("<hierarchy>QR_CANARY", scenario="login_wait", mode=mode)
                self.assertEqual(code, 2)
                self.assertEqual(report["outcome"], "capture_unavailable")

    def test_invalid_arguments_do_not_echo(self):
        self.assertEqual(self.invoke(source="URL_CANARY"),
                         (2, {"outcome": "invalid_input"}))

    def test_rejects_foreign_duplicate_invalid_or_changed_sessions(self):
        valid = media(5_000, 52_000)
        for raw in (media(5_000, 52_000, package="another.app"), valid + valid,
                    valid.replace("active=true", "active=false")):
            self.assertIsNone(CHECK.media_position(raw.encode()))
        first = CHECK.media_position(valid.encode())
        for raw in (media(8_000, 55_000, session=8), media(8_000, 52_000),
                    media(28_000, 55_000), media(3_000, 55_000),
                    media(8_000, 55_000, "PAUSED(2)")):
            self.assertIsNone(CHECK.playback_progress(first, CHECK.media_position(raw.encode())))
        self.assertIs(CHECK.playback_progress(first, first), False)
