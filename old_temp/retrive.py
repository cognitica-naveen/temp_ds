# Read the decoded video buffers from a sample mp4 file
from pyservicemaker import Pipeline, Flow, BufferRetriever

class MyBufferRetriever(BufferRetriever):
    def __init__(self):
        super().__init__()
        self.frames = 0

    def consume(self, buffer):
        print(">>> consume() called")

        tensor = buffer.extract(0)

        print("Shape:", tensor.shape)
        print("Frames before:", self.frames)

        assert len(tensor.shape) == 3

        self.frames += 1

        # print("Frames after:", self.frames)

        return 1
    # def consume(self, buffer):
    #     tensor = buffer.extract(0)
    #     assert len(tensor.shape) == 3
    #     self.frames += 1
    #     return 1
video_file = "/opt/nvidia/deepstream/deepstream/samples/streams/sample_1080p_h264.mp4"
Flow(Pipeline("retrieve")).capture([video_file]).retrieve(MyBufferRetriever())()