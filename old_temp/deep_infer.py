from pyservicemaker import Pipeline, Flow, BufferProvider, Buffer


# streaming a udp stream via rtsp
# pipeline = Pipeline("test")
# video_file = "/opt/nvidia/deepstream/deepstream/samples/streams/sample_1080p_h264.mp4"
# Flow(pipeline).capture([video_file]).encode("output.mp4", sync=True)()


pgie_config = "/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_infer_primary.yml"
# object detection using resnet18 for 4 streams
uri_list = ["/opt/nvidia/deepstream/deepstream/samples/streams/sample_1080p_h264.mp4"]*4
Flow(Pipeline("infer")).batch_capture(uri_list).infer(pgie_config).render()()