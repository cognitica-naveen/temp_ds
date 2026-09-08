
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
import cv2

app = FastAPI()

RTSP_URL = "rtsp://admin:Cogn%21%402023@192.168.1.104:554/video/live?channel=1&subtype=0"


def generate_frames():
    cap = cv2.VideoCapture(RTSP_URL)

    if not cap.isOpened():
        print("Failed to open RTSP stream")
        return

    while True:
        ret, frame = cap.read()

        if not ret:
            print("Failed to read frame")
            break

        # Resize if required
        frame = cv2.resize(frame, (1280, 720))

        # Convert frame to JPEG
        ret, buffer = cv2.imencode(
            ".jpg",
            frame,
            [cv2.IMWRITE_JPEG_QUALITY, 80]
        )

        if not ret:
            continue

        frame_bytes = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + frame_bytes
            + b"\r\n"
        )

    cap.release()


@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>RTSP Camera</title>
    </head>

    <body>
        <h2>RTSP Camera</h2>

        <img
            src="/video"
            width="1280"
            height="720"
        />

    </body>
    </html>
    """


@app.get("/video")
def video():
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )