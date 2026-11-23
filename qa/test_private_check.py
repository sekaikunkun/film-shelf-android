import importlib.util
import json
import os
from pathlib import Path
from copy import deepcopy
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
from copy import deepcopy
a = sys.argv[1:]
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
elif a[4:7] == ['-s','emulator-5678','exec-out']:
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


def sample(position=None, login=False, lookalike=False, preview=None):
    root = ET.Element("hierarchy")
    for field, canary in zip(("api", "token", "name", "code"), MARKERS):
        ET.SubElement(root, "node", package=CHECK.PACKAGE,
                      text="https://example.invalid/" + canary,
                      attrib={"resource-id": CHECK.PACKAGE + ":id/" + field,
                              "content-desc": canary})
    def node(parent, rid, text=""):
        return ET.SubElement(parent, "node", package=CHECK.PACKAGE, text=text,
                             attrib={"resource-id": CHECK.PACKAGE + ":id/" + rid})

    if position:
        node(node(node(root, "control"), "seek"), "position", position)
    if preview:
        node(node(root, "center"), "position", preview)
    if login or lookalike:
        for rid, value in zip(("alertTitle", "message", "button2", "button1"),
                              ("需要扫码或登录", "完成验证后，选择重试播放。", "继续等待", "重试播放")):
            ET.SubElement(root, "node", package=CHECK.PACKAGE, text=value,
                          attrib={"resource-id": CHECK.PACKAGE + ":id/" + (rid if login else "name")})
    return ET.tostring(root, encoding="unicode")


class PrivateCheckTest(unittest.TestCase):
    def invoke(self, one="", two="", scenario="playback", mode="ok", source="A"):
        with tempfile.TemporaryDirectory() as scratch:
            adb = Path(scratch) / "adb"
            adb.write_text(FAKE_ADB)
            adb.chmod(0o700)
            for suffix, payload in ((".first", one), (".second", two)):
                adb.with_name("next").with_suffix(suffix).write_text(payload, encoding="utf-8")
            result = subprocess.run([sys.executable, str(SCRIPT), "--adb", str(adb),
                                     "--port", "15084", "--serial", "emulator-5678",
                                     "--source", source, "--scenario", scenario],
                                    env=dict(os.environ, MODE=mode, ADB_SERVER_SOCKET="don't forward"),
                                    capture_output=True, text=True, timeout=16)
            self.assertEqual(result.stderr, "")
            for canary in MARKERS:
                self.assertNotIn(canary, result.stdout + result.stderr)
            self.assertEqual(len(result.stdout.splitlines()), 1)
            return result.returncode, json.loads(result.stdout)

    def test_playback_and_login_path_emit_only_fixed_report(self):
        for one, two, scenario, expected, progress in (
            (sample("00:05", lookalike=True, preview="00:15"), sample("00:08", preview="00:30"), "playback", "pass", True),
            (sample(preview="00:15"), sample(preview="00:30"), "playback", "unconfirmed", None),
            (sample("00:05"), sample(), "playback", "unconfirmed", None),
            (sample("00:05", preview="00:15"), sample("00:05", preview="00:30"), "playback", "unconfirmed", False),
            (sample(login=True), sample(login=True), "login_wait", "requires_login", None),
            (sample("00:05"), sample("00:05"), "playback", "unconfirmed", False),
            (sample("00:52"), sample("00:01"), "playback", "unconfirmed", None),
        ):
            with self.subTest(scenario=scenario, expected=expected):
                code, report = self.invoke(one, two, scenario)
                self.assertEqual(code, 0)
                self.assertEqual(report, {"source": "A", "scenario": scenario, "outcome": expected,
                                          "progress_advanced": progress})

    def test_errors_and_timeout_never_echo_raw_capture(self):
        for mode in ("error", "oversize", "multiple", "timeout", "ok"):
            with self.subTest(mode=mode):
                code, report = self.invoke("<hierarchy>QR_CANARY", mode=mode)
                self.assertEqual(code, 2)
                self.assertEqual(report["outcome"], "capture_unavailable")

    def test_invalid_arguments_do_not_echo(self):
        self.assertEqual(self.invoke(source="URL_CANARY"),
                         (2, {"outcome": "invalid_input"}))

    def test_rejects_foreign_position_and_ambiguous_clock(self):
        data = sample("00:32").replace('package="' + CHECK.PACKAGE, 'package="another.app')
        self.assertEqual(CHECK.decode_snapshot(data.encode()), (False, None))
        data = sample("00:32")
        tree = ET.fromstring(data)
        tree.append(deepcopy(tree[-1]))
        self.assertEqual(CHECK.decode_snapshot(ET.tostring(tree)), (False, None))
