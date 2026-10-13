#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
exec python3 db/verify_worldcup.py
