"""
Detection snapshot saver.

A BufferOperator probe that walks NvDs batch metadata, matches detections
against per-camera rules from camera.config.yaml, and saves images to
data/<class>/<camera>-<timestamp>.jpg.

Two capture styles (set in camera.config.yaml per rule):

    save_mode: "frame"  -> full frame with bounding boxes drawn (default)
    save_mode: "crop"   -> cropped object only

Rules in camera.config.yaml look like:

    detections:
      - camera: cam-0          # pipeline name (cam-N) or "all"
        classes: [person]      # class label names from labels.txt
        threshold: 0.5         # min confidence
        save_image: true       # false = count only, no image
        save_mode: frame       # "frame" (bbox on full frame) or "crop"

Class label folders are created automatically under data/.

PERFORMANCE NOTE:
    The probe callback runs on a GStreamer streaming thread. Encoding a
    1080p JPEG takes ~30-50ms, which cannot keep up with 24 fps input —
    so the heavy work (GPU->CPU copy is unavoidable in-callback, but
    cvtColor + drawing + disk write) is handed to a background writer
    thread. The callback only snapshots the latest frame and returns.
"""

import os
import queue
import threading
import time
from collections import defaultdict

import cv2
import numpy as np

from pyservicemaker import BufferOperator

# BGR colors for bbox drawing (cycled by class name hash)
_COLORS = [
    (0, 128, 255),    # orange
    (255, 0, 0),      # blue
    (0, 255, 0),      # green
    (0, 0, 255),      # red
    (255, 0, 255),    # magenta
    (0, 255, 255),    # yellow
]


class DetectionSaver(BufferOperator):
    """BufferOperator that saves detection images per camera/class/threshold."""

    def __init__(self, camera_name, rules, labels, data_dir,
                 min_box_size=32, cooldown=2.0, max_per_minute=30,
                 writer_threads=2):
        super().__init__()
        self.camera_name = camera_name
        self.labels = labels                    # class_id -> label
        self.data_dir = data_dir
        self.min_box_size = min_box_size        # skip tiny/unreliable boxes
        self.cooldown = cooldown                # seconds between saves per class
        self.max_per_minute = max_per_minute    # safety cap per class
        self.counts = defaultdict(int)

        # rules for this camera: {label: {threshold, save_image, save_mode}}
        self.rules = {}
        for r in rules:
            targets = [r.get("camera", "all")]
            if "all" not in targets and camera_name not in targets:
                continue
            for cls in r.get("classes", []):
                self.rules[cls] = {
                    "threshold": float(r.get("threshold", 0.5)),
                    "save_image": bool(r.get("save_image", True)),
                    "save_mode": str(r.get("save_mode", "frame")).lower(),
                }
        self._last_save = defaultdict(float)
        self._minute_window = defaultdict(list)

        # Background writer pool: keeps the GStreamer thread non-blocking.
        # Bounded queue drops oldest jobs when writers fall behind.
        self._jobs = queue.Queue(maxsize=64)
        self._writer_threads = []
        for i in range(writer_threads):
            t = threading.Thread(target=self._writer_loop,
                                 name=f"{camera_name}-writer-{i}", daemon=True)
            t.start()
            self._writer_threads.append(t)

    # ------------------------------------------------------------------
    # Background writer
    # ------------------------------------------------------------------

    def _writer_loop(self):
        while True:
            job = self._jobs.get()
            if job is None:          # shutdown sentinel
                return
            kind, frame, detections, frame_w, frame_h, label, now = job
            try:
                if kind == "frame":
                    self._encode_and_write_frame(frame, detections,
                                                 frame_w, frame_h, label, now)
                else:
                    self._encode_and_write_crop(frame, frame_w, frame_h,
                                                label, now)
            except Exception as e:
                print(f"[{self.camera_name}] writer error: {e}")

    def _encode_and_write_frame(self, frame, detections, frame_w, frame_h,
                                label, now):
        path = self._out_path(label, now)
        out = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        for l, conf, rect in detections:
            self._draw_bbox(out, rect, l, conf, frame_w, frame_h)
        cv2.imwrite(path, out, [cv2.IMWRITE_JPEG_QUALITY, 90])

    def _encode_and_write_crop(self, frame, frame_w, frame_h, label, now):
        # rect is stored inside job detections for crop mode
        path = self._out_path(label, now)
        cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, 90])

    # ------------------------------------------------------------------
    # Rule helpers
    # ------------------------------------------------------------------

    def _wants(self, label):
        """Rule dict for a label, or None if not subscribed."""
        return self.rules.get(label) or self.rules.get("*")

    def _rate_ok(self, label, now):
        if now - self._last_save[label] < self.cooldown:
            return False
        window = self._minute_window[label]
        window[:] = [t for t in window if now - t < 60]
        if len(window) >= self.max_per_minute:
            return False
        return True

    def _mark_saved(self, label, now):
        self._last_save[label] = now
        self._minute_window[label].append(now)
        self.counts[label] += 1

    def _draw_bbox(self, frame, rect, label, confidence, frame_w, frame_h):
        """Draw one detection box + label on the frame (in place)."""
        left = max(0, int(rect.left))
        top = max(0, int(rect.top))
        right = min(frame_w - 1, int(rect.left + rect.width))
        bottom = min(frame_h - 1, int(rect.top + rect.height))
        color = _COLORS[hash(label) % len(_COLORS)]
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        text = f"{label} {confidence:.2f}"
        (tw, th), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX,
                                             0.5, 1)
        ty = top - baseline - 4 if top - th - 4 > 0 else bottom + th + 4
        cv2.rectangle(frame, (left, ty - th - 2), (left + tw + 2, ty + baseline),
                      color, -1)
        cv2.putText(frame, text, (left + 1, ty), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (0, 0, 0), 1, cv2.LINE_AA)

    def _out_path(self, label, now):
        out_dir = os.path.join(self.data_dir, label)
        os.makedirs(out_dir, exist_ok=True)
        ts = time.strftime("%Y%m%d-%H%M%S") + f"-{int(now * 1000) % 1000:03d}"
        return os.path.join(out_dir, f"{self.camera_name}-{label}-{ts}.jpg")

    # ------------------------------------------------------------------
    # Probe callback — must stay FAST (no disk I/O, no JPEG encoding)
    # ------------------------------------------------------------------

    def handle_buffer(self, buffer):
        batch_meta = getattr(buffer, "batch_meta", None)
        if batch_meta is None:
            return True

        for frame_meta in batch_meta.frame_items:
            hits = []
            for obj in frame_meta.object_items:
                label = self.labels[obj.class_id] \
                    if 0 <= obj.class_id < len(self.labels) else str(obj.class_id)
                rule = self._wants(label)
                if rule is None or obj.confidence < rule["threshold"]:
                    continue
                hits.append((label, obj.confidence, obj.rect_params, rule))

            if not hits:
                continue

            now = time.time()
            active = [(l, c, r, rule) for l, c, r, rule in hits
                      if self._rate_ok(l, now)]
            if not active:
                continue

            frame_np = self._frame_to_numpy(buffer, frame_meta)
            if frame_np is None:
                continue

            frame_h, frame_w = frame_np.shape[:2]

            # Count-only rules: mark immediately, no image
            image_jobs = []
            for label, confidence, rect, rule in active:
                if not rule["save_image"]:
                    self._mark_saved(label, now)
                    continue
                image_jobs.append((label, confidence, rect, rule))

            if not image_jobs:
                continue

            if image_jobs[0][3]["save_mode"] == "crop":
                # crop mode: one job per detection (crop drawn from frame)
                for label, confidence, rect, rule in image_jobs:
                    left = max(0, int(rect.left))
                    top = max(0, int(rect.top))
                    right = min(frame_w, int(rect.left + rect.width))
                    bottom = min(frame_h, int(rect.top + rect.height))
                    if (right - left < self.min_box_size
                            or bottom - top < self.min_box_size):
                        continue
                    crop = np.ascontiguousarray(frame_np[top:bottom, left:right])
                    self._enqueue(("crop", crop, None, 0, 0, label, now))
                    self._mark_saved(label, now)
            else:
                # frame mode: copy once, draw ALL boxes, save one file
                frame_copy = frame_np.copy()
                dets = [(l, c, r) for l, c, r, _ in image_jobs]
                self._enqueue(("frame", frame_copy, dets, frame_w, frame_h,
                               image_jobs[0][0], now))
                for l, _, _, _ in image_jobs:
                    self._mark_saved(l, now)

        return True

    def _enqueue(self, job):
        try:
            self._jobs.put_nowait(job)      # drop oldest when saturated
        except queue.Full:
            try:
                self._jobs.get_nowait()     # discard oldest
                self._jobs.put_nowait(job)
            except (queue.Empty, queue.Full):
                pass

    # ------------------------------------------------------------------
    # Frame extraction
    # ------------------------------------------------------------------

    def _frame_to_numpy(self, buffer, frame_meta):
        """Extract the frame tensor and convert to an HxWx3 numpy RGB array.

        The extracted tensor lives on the GPU; its __dlpack__ needs a CUDA
        stream argument, so np.from_dlpack() cannot consume it directly.
        torch.from_dlpack handles the conversion; fall back gracefully if
        torch is unavailable.
        """
        try:
            tensor = buffer.extract(frame_meta.batch_id)
            try:
                import torch
                arr = torch.from_dlpack(tensor).cpu().numpy()
            except ImportError:
                arr = np.from_dlpack(tensor.to_gpu("cpu"))
        except Exception:
            return None
        if arr.ndim != 3:
            return None
        if arr.shape[2] == 3:            # HxWx3
            return arr
        if arr.shape[0] == 3:            # 3xHxW (planar)
            return arr.transpose(1, 2, 0)
        return None
