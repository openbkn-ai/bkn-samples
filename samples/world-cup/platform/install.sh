#!/bin/sh
# Platform hook. Reads BKN_SAMPLE_INPUT and does not call kubectl.
set -eu
cd "$(dirname "$0")/.."
exec python3 platform/install_worldcup.py
