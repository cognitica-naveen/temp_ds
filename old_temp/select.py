from pyservicemaker import Flow, MediaType, Pipeline

# Capture both media types from an audio/video file, then keep only the
# audio branch and encode it to a WAV file.
av_file = "/opt/nvidia/deepstream/deepstream/samples/streams/sample_720p.mp4"
Flow(Pipeline("select-audio")).capture(
    [av_file],
    media_types=(MediaType.VIDEO, MediaType.AUDIO),
).select(MediaType.AUDIO).encode("audio.wav")()