from pyservicemaker import Pipeline, Flow, Probe, BatchMetadataOperator

from pyservicemaker import BatchMetadataOperator, Probe, osd

class ObjectCounterMarker(BatchMetadataOperator):
    def handle_metadata(self, batch_meta):
        # Iterate through every frame in the batched buffer
        for frame_meta in batch_meta.frame_items:
            vehicle_count = 0
            person_count = 0
            
            # Count detected objects based on class IDs from the inference engine
            for object_meta in frame_meta.object_items:
                class_id = object_meta.class_id
                if class_id == 0:     # Example: Class 0 mapped to Vehicles
                    vehicle_count += 1
                elif class_id == 2:   # Example: Class 2 mapped to Persons
                    person_count += 1
            
            # Print frame details to the console log
            print(f"Object Counter: Pad Idx={frame_meta.pad_index}, "
                  f"Frame Number={frame_meta.frame_number}, "
                  f"Vehicle Count={vehicle_count}, Person Count={person_count}")
            
            # Formulate text to burn onto the visual frame via OSD
            text = f"Person={person_count}, Vehicle={vehicle_count}"
            
            # Logic to attach metadata back to display_meta goes here...

pgie_config = "/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_infer_primary.yml"
uri_list = ["/opt/nvidia/deepstream/deepstream/samples/streams/sample_1080p_h264.mp4"]*4
pipeline = Pipeline("analytics")
flow = Flow(pipeline).batch_capture(uri_list).infer(pgie_config)
flow = flow.track(ll_config_file="/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_tracker_NvDCF_perf.yml", ll_lib_file="/opt/nvidia/deepstream/deepstream/lib/libnvds_nvmultiobjecttracker.so")
# Analyze the video frames and detected objects
flow = flow.analyze("/opt/nvidia/deepstream/deepstream/sources/apps/sample_apps/deepstream-nvdsanalytics-test/config_nvdsanalytics.txt")
# Attach a probe to retrieve analytics info and render
flow.attach(what=Probe("counter", ObjectCounterMarker())).render()()
flow()