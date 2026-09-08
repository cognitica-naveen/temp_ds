
from pyservicemaker import Pipeline, Flow

uri_list = ["/opt/nvidia/deepstream/deepstream/samples/streams/sample_1080p_h264.mp4"]*4
# playback all the source in a tiled display
Flow(Pipeline("playback")).capture(uri_list).batch().render()()