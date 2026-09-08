from pyservicemaker import Pipeline, Flow

# Initiate a pipeline to read a mp4 file
# transcode the video to both a local file and via rtsp
# at the same time, do the playback
pipeline = Pipeline("test")
dest = "rtsp://localhost:8554"
flow = Flow(pipeline).capture(["/opt/nvidia/deepstream/deepstream/samples/streams/sample_1080p_h265.mp4"]).batch().fork()
flow.encode(dest, sync=True)
flow.encode("/tmp/sample.mp4")
flow.render(sync=True)
flow()