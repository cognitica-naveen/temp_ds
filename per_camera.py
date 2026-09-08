"""
Per-camera inference streams, driven by camera.config.yaml.

Reads the camera list and detection rules from camera.config.yaml and
starts one DeepStream pipeline per camera, each publishing its annotated
output as RTSP:

    camera i -> rtsp://<host>:{BASE_PORT + i}/cam-{i}

Detection snapshots: for each camera you can subscribe to classes with a
confidence threshold and enable/disable image saving. Saved crops go to
data/<class>/<camera>-<timestamp>.jpg (folders created automatically).

Then regenerates mediamtx.yml path entries for every camera, so MediaMTX
serves each at  http://<host>:8889/cam-{i}  (WebRTC) / :8888 (HLS).

Change camera.config.yaml and restart:
    ./start_stack.sh
"""

import os
import re
import signal
import subprocess
import sys
import tempfile

import yaml

from pyservicemaker import Pipeline, Flow, RenderMode, Probe

from detection_saver import DetectionSaver

HERE = os.path.dirname(os.path.abspath(__file__))
CAMERA_CONFIG = os.path.join(HERE, "camera.config.yaml")
MEDIAMTX_CONFIG = os.path.join(HERE, "mediamtx.yml")
DATA_DIR = os.path.join(HERE, "data")

PGIE_CONFIG = "/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_infer_primary.yml"
PGIE_MODEL_DIR = "/opt/nvidia/deepstream/deepstream/samples/models/Primary_Detector"

# Base RTSP output port; camera i publishes on BASE_PORT + i
BASE_PORT = 8556

pipelines = []


def load_config():
    with open(CAMERA_CONFIG) as f:
        cfg = yaml.safe_load(f) or {}
    cameras = cfg.get("cameras") or []
    detections = cfg.get("detections") or []
    if not cameras:
        print("No cameras listed in camera.config.yaml — nothing to run.")
        sys.exit(1)
    return cameras, detections


def load_labels():
    """Load class labels from the detector's labels.txt (class_id order)."""
    labels_file = os.path.join(PGIE_MODEL_DIR, "labels.txt")
    with open(labels_file) as f:
        return [line.strip() for line in f if line.strip()]


def update_mediamtx_config(n_cameras):
    """Rewrite the paths: block in mediamtx.yml to match the camera count."""
    with open(MEDIAMTX_CONFIG) as f:
        content = f.read()

    entries = [
        "  ds-test:",
        "    source: rtsp://localhost:8556/ds-test",
        "    sourceOnDemand: yes",
        "",
    ]
    for i in range(n_cameras):
        entries += [
            f"  cam-{i}:",
            f"    source: rtsp://localhost:{BASE_PORT + i}/cam-{i}",
            "    sourceOnDemand: yes",
        ]

    # Replace everything from "paths:" up to the "all_others:" sentinel
    paths_block = "paths:\n" + "\n".join(entries) + "\n"
    pattern = re.compile(r"^paths:.*?(?=  all_others:)", re.S | re.M)
    if pattern.search(content):
        content = pattern.sub(paths_block + "\n", content)
    else:
        content += "\n" + paths_block

    # Atomic write so MediaMTX never sees a half-written file
    fd, tmp = tempfile.mkstemp(dir=HERE, text=True)
    with os.fdopen(fd, "w") as f:
        f.write(content)
    os.replace(tmp, MEDIAMTX_CONFIG)
    print(f"mediamtx.yml updated: {n_cameras} camera paths (cam-0 .. cam-{n_cameras - 1})")


def restart_mediamtx():
    """Restart MediaMTX so it picks up the regenerated path list."""
    subprocess.run(["pkill", "-9", "-f", "mediamtx mediamtx.yml"], check=False)
    subprocess.Popen(
        ["setsid", "nohup", "./mediamtx", "mediamtx.yml"],
        cwd=HERE,
        stdout=open("/tmp/mtx.log", "w"),
        stderr=subprocess.STDOUT,
    )


def build_pipeline(uri, index, detections, labels):
    """One independent pipeline: capture -> infer -> probe -> RTSP out."""
    camera_name = f"cam-{index}"
    pipeline = Pipeline(camera_name)
    flow = Flow(pipeline) \
        .batch_capture([uri], live_source=True) \
        .infer(PGIE_CONFIG)

    # Attach the detection-snapshot probe if any rule targets this camera.
    # The probe needs RGB pixels, but the pipeline after nvinfer carries
    # NVMM/NV12 buffers. Add a converter + RGB capsfilter branch for the
    # probe, then tee back into the normal render path (same pattern as
    # Flow.retrieve()).
    rules_for_cam = [
        r for r in detections
        if r.get("camera", "all") in ("all", camera_name)
    ]
    if rules_for_cam:
        saver = DetectionSaver(camera_name, rules_for_cam, labels, DATA_DIR)
        probe = Probe(f"{camera_name}-saver", saver)

        infer_origin = flow._streams[0].originator
        convert = f"{camera_name}-save-convert"
        caps = f"{camera_name}-save-caps"
        tee = f"{camera_name}-tee"
        q_render = f"{camera_name}-q-render"

        pipeline.add("nvvideoconvert", convert, {"gpu-id": 0, "compute-hw": 1})
        pipeline.add("capsfilter", caps,
                     {"caps": "video/x-raw(memory:NVMM), format=RGB"})
        pipeline.add("tee", tee)
        pipeline.add("queue", q_render)

        pipeline.link(infer_origin, convert)
        pipeline.link(convert, caps)
        pipeline.link(caps, tee)
        pipeline.link((tee, q_render), ("", ""))
        # Probe observes buffers on the capsfilter's source pad (always
        # flowing into the tee). Do NOT attach to a dead-end queue: a queue
        # with no downstream sink never pushes buffers out, so a probe there
        # would fire almost never.
        pipeline.attach(caps, probe)

        # The render branch continues from the render queue
        flow = Flow(pipeline, streams=[type(flow._streams[0])(q_render,
                    media_type="video")])
        subscribed = sorted({c for r in rules_for_cam for c in r.get("classes", [])})
        print(f"[{camera_name}] detection saver attached for classes: {subscribed}")

    flow.render(mode=RenderMode.STREAM,
                rtsp_port=BASE_PORT + index,
                rtsp_mount_point=camera_name,
                sync=False)
    return pipeline


def main():
    cameras, detections = load_config()
    n = len(cameras)
    labels = load_labels()
    print(f"Loaded {n} camera(s) from camera.config.yaml")
    print(f"Detector classes: {labels}")

    update_mediamtx_config(n)
    restart_mediamtx()

    for i, uri in enumerate(cameras):
        p = build_pipeline(uri, i, detections, labels)
        p.start()
        pipelines.append(p)
        print(f"[cam-{i}] started -> rtsp://0.0.0.0:{BASE_PORT + i}/cam-{i}")

    def shutdown(signum, frame):
        print("\nShutting down pipelines...")
        for p in pipelines:
            try:
                p.stop()
            except Exception:
                pass
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Block forever; KeyboardInterrupt is handled by the signal handler
    signal.pause()


if __name__ == "__main__":
    main()
