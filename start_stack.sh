#!/bin/bash
# Start / restart the whole stack based on camera.config.yaml.
#
#   1 camera in config  -> 1 per-camera stream
#  12 cameras in config -> 12 per-camera streams
#
# per_camera.py regenerates mediamtx.yml paths automatically before
# MediaMTX starts, and webserver.py serves the dynamic grid.
#
# Logs: /tmp/percam.log, /tmp/mtx.log, /tmp/web.log

set -e
cd "$(dirname "$0")"

echo "Stopping old processes..."
pkill -f "per_camera.py" 2>/dev/null || true
pkill -f "mediamtx mediamtx.yml" 2>/dev/null || true
pkill -f "webserver.py" 2>/dev/null || true
pkill -f "http.server 800" 2>/dev/null || true
sleep 2

echo "Starting per-camera pipelines (from camera.config.yaml)..."
setsid nohup python3 per_camera.py > /tmp/percam.log 2>&1 &

echo "Starting web server on :8000..."
setsid nohup python3 webserver.py > /tmp/web.log 2>&1 &

echo "Done. Logs:"
echo "  tail -f /tmp/percam.log   # DeepStream pipelines"
echo "  tail -f /tmp/mtx.log      # MediaMTX"
echo "  tail -f /tmp/web.log      # web server"
echo
echo "Grid page: http://<this-host>:8000/per_camera.html"
