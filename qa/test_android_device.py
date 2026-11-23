import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


FAKE_ADB = """#!/usr/bin/env python3
import os, sys
args = sys.argv[1:]
assert args[:4] == ['-H', '127.0.0.1', '-P', '15084']
assert not any(os.environ.get(k) for k in ('ADB_SERVER_SOCKET', 'ANDROID_ADB_SERVER_PORT', 'ANDROID_SERIAL'))
if args[4:] == ['devices']:
    print('List of devices attached')
    print(os.environ['FAKE_DEVICES'])
    sys.exit(0)
assert args[4:6] == ['-s', 'emulator-5678']
props = {('getprop', 'ro.kernel.qemu'): os.environ['FAKE_IS_EMULATOR'],
         ('getprop', 'ro.product.cpu.abi'): 'arm64-v8a',
         ('getprop', 'ro.build.version.sdk'): '35',
         ('getconf', 'PAGE_SIZE'): '16384'}
if args[6] == 'shell' and tuple(args[7:]) in props:
    print(props[tuple(args[7:])])
else:
    raise RuntimeError('unexpected ADB command')
"""


class DeviceBridgeTest(unittest.TestCase):
    def run_bridge(self, devices, qemu="1", serial="emulator-5678", port="15084"):
        with tempfile.TemporaryDirectory() as scratch:
            adb = Path(scratch) / "adb"
            adb.write_text(FAKE_ADB, encoding="utf-8")
            adb.chmod(0o700)
            env = dict(os.environ, FAKE_DEVICES=devices, FAKE_IS_EMULATOR=qemu,
                       ANDROID_SERIAL="not-this-device", ADB_SERVER_SOCKET="not-this-server")
            return subprocess.run([sys.executable, str(Path(__file__).with_name("android-device.py")),
                                   "--adb", str(adb), "--port", port, "--serial", serial, "device"],
                                  env=env, capture_output=True, text=True, timeout=10)

    def test_probes_only_explicit_emulator(self):
        result = self.run_bridge("emulator-5678\tdevice")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"serial": "emulator-5678", "api": "35",
                                                     "abi": "arm64-v8a", "page_size": "16384"})

    def test_rejects_wrong_multiple_offline_and_physical_targets(self):
        pairs = [
            ("emulator-5679\tdevice", "1"),
            ("emulator-5678\tdevice\nUSB123\tdevice", "1"),
            ("emulator-5678\toffline", "1"),
            ("emulator-5678\tdevice", "0"),
        ]
        for devices, qemu in pairs:
            with self.subTest(devices=devices, qemu=qemu):
                result = self.run_bridge(devices, qemu)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("Traceback", result.stderr)

    def test_rejects_default_server_and_nonemulator_serial(self):
        for kwargs in ({"port": "5037"}, {"serial": "USB123"}):
            with self.subTest(**kwargs):
                self.assertEqual(self.run_bridge("", **kwargs).returncode, 2)
