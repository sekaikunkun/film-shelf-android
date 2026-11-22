#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
revision=d187f6ae8bfaf0a4720724281d0a91186c57f73d
out="${1:?fresh destination required}"
mkdir -p "$out"
if [[ -n "$(ls -A -- "$out")" ]]; then echo "Destination must be empty" >&2; exit 1; fi
archive="$(mktemp)"
trap 'rm -f -- "$archive"' EXIT
curl --fail --silent --show-error --location --retry 3 "https://codeload.github.com/webhtv/webhtv/tar.gz/$revision" -o "$archive"
tar --extract --gzip --file="$archive" --strip-components=1 --directory="$out"
cd "$out"
git apply --check "$root/patches/film-shelf.patch"
git apply "$root/patches/film-shelf.patch"
rm -f app/libs/forcetech-release.aar
bash "$root/scripts/fetch-wheels.sh"
