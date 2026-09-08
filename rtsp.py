from pyservicemaker import Pipeline, Flow, BufferRetriever, RenderMode


class MyBufferRetriever(BufferRetriever):

    def __init__(self):
        super().__init__()
        self.frames = 0

    def consume(self, buffer):

        self.frames += 1

        print(f"\n========== FRAME {self.frames} ==========")

        try:
            frame = buffer.extract(0)

            print("Frame:", frame)
            print("Shape:", frame.shape)
            print("Dtype:", frame.dtype)

            try:
                print("DLPack device:", frame.__dlpack_device__())
            except Exception as e:
                print("DLPack device unavailable:", e)

        except Exception as e:
            print("Frame extraction error:", e)

        return 1


RTSP_URL = "rtsp://admin:Cogn%21%402023@192.168.1.112:554/video/live?channel=1&subtype=0"
# Flow(pipeline).capture([camera_uri]).render()()


CAMERAS = [
    "rtsp://admin:Cogn%21%402023@192.168.1.112:554/video/live?channel=1&subtype=0",
    "rtsp://admin:Cogn%21%402023@192.168.1.115:554/video/live?channel=1&subtype=0",
    "rtsp://admin:Cogn%21%402023@192.168.1.102:554/video/live?channel=1&subtype=0",
    "rtsp://admin:Cogn%21%402023@192.168.1.104:554/video/live?channel=1&subtype=0",
    "rtsp://admin:Cogn%21%402023@192.168.1.118:554/video/live?channel=1&subtype=0",
    "rtsp://admin:Cogni_2018@192.168.1.130:554/video/live?channel=1&subtype=0",
    "rtsp://admin:Cogn%21%402023@192.168.1.114:554/video/live?channel=1&subtype=0",
    "rtsp://admin:Cogn%21%402023@192.168.1.115:554/video/live?channel=1&subtype=0",
]



pgie_config = "/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_infer_primary.yml"


pipeline = Pipeline("rtsp-reader")

Flow(pipeline) \
    .batch_capture(CAMERAS, live_source=True) \
    .infer(pgie_config) \
    .render(mode=RenderMode.STREAM, rtsp_port=8556, rtsp_mount_point="ds-test", sync=False)()
    # .retrieve(MyBufferRetriever()) \


# pipeline = Pipeline("rtsp")
# Flow(pipeline).capture([RTSP_URL]).retrieve(MyBufferRetriever())()