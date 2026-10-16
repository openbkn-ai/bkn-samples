#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
exec python3 platform/sample_platform.py verify
