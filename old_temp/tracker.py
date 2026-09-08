from pyservicemaker import Pipeline, Flow

pgie_config = "/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_infer_primary.yml"
uri_list = ["/opt/nvidia/deepstream/deepstream/samples/streams/sample_1080p_h264.mp4"]*4
# object detection and tracking using nvmultiobjecttracker for 4 streams
Flow(Pipeline("tracker")).batch_capture(uri_list).infer(pgie_config).track(
    ll_config_file="/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_tracker_NvDCF_perf.yml",
    ll_lib_file="/opt/nvidia/deepstream/deepstream/lib/libnvds_nvmultiobjecttracker.so"
).render()()