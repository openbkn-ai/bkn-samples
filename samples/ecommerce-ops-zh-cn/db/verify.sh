#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
exec python3 db/database.py verify
