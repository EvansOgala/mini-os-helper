#!/usr/bin/env sh
set -eu

APP_DIR="/app/share/org.evans.MiniOSHelper"
cd "$APP_DIR"
exec python3 main.py
