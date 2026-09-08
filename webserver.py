#!/usr/bin/env python3
"""
Tiny web server for the per-camera grid.

Serves the workspace files on :8000 and exposes /cameras.json generated
from camera.config.yaml, so the HTML grid always matches the running
camera count without any hardcoding.

Start with the rest of the stack (see start_stack.sh).
"""

import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
CAMERA_CONFIG = os.path.join(HERE, "camera.config.yaml")
PORT = 8000


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=HERE, **kwargs)

    def do_GET(self):
        if self.path == "/cameras.json":
            try:
                with open(CAMERA_CONFIG) as f:
                    cfg = yaml.safe_load(f) or {}
                cameras = cfg.get("cameras") or []
            except FileNotFoundError:
                cameras = []
            names = [f"cam-{i}" for i in range(len(cameras))]
            body = json.dumps({"cameras": names}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()

    def log_message(self, fmt, *args):
        pass  # keep the log quiet


if __name__ == "__main__":
    print(f"Serving {HERE} on http://0.0.0.0:{PORT} (cameras.json at /cameras.json)")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
