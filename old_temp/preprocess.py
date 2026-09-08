from pyservicemaker import Pipeline, Flow


preprocess_config = "/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_preprocess.yml"
Flow(Pipeline("preprocess")).batch_capture(
    ["/opt/nvidia/deepstream/deepstream/samples/streams/sample_1080p_h264.mp4"]
).preprocess(preprocess_config).infer(
    "/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_infer_primary.yml"
).render()()