#!/usr/bin/env bash
set -euo pipefail
mkdir -p chaquo/wheels
cd chaquo/wheels
curl -fL --retry 2 'https://github.com/FongMi/python-android/releases/download/v1.1.0/chaquopy_libxml2-2.9.8-4-py3-none-android_24_arm64_v8a.whl' -o 'chaquopy_libxml2-2.9.8-4-py3-none-android_24_arm64_v8a.whl'
echo '9ef0c8a879ce28a6fb8eb3dbc69b32110cce06070133950bdaff6d9782e44082  chaquopy_libxml2-2.9.8-4-py3-none-android_24_arm64_v8a.whl' | sha256sum -c
curl -fL --retry 2 'https://github.com/FongMi/python-android/releases/download/v1.1.0/chaquopy_libxslt-1.1.32-4-py3-none-android_24_arm64_v8a.whl' -o 'chaquopy_libxslt-1.1.32-4-py3-none-android_24_arm64_v8a.whl'
echo '71da8f8cfe4dcc104da87cb8421b7d3bb9d3cb8857c75541c1da7a1ed6855a62  chaquopy_libxslt-1.1.32-4-py3-none-android_24_arm64_v8a.whl' | sha256sum -c
curl -fL --retry 2 'https://github.com/FongMi/python-android/releases/download/v1.1.0/lxml-5.3.0-2-cp310-cp310-android_24_arm64_v8a.whl' -o 'lxml-5.3.0-2-cp310-cp310-android_24_arm64_v8a.whl'
echo 'a03773e22d08f73887dcc2909f536b4630297a965ae7f045b7c48e81becfdffa  lxml-5.3.0-2-cp310-cp310-android_24_arm64_v8a.whl' | sha256sum -c
