from pyservicemaker import BufferProvider, Buffer
from pyservicemaker import Pipeline, Flow, Probe, BatchMetadataOperator

class MyBufferProvider(BufferProvider):

    def __init__(self, width, height, device='cpu', framerate=30, format="RGB"):
        super().__init__()
        self.width = width
        self.height = height
        self.format = format
        self.framerate = framerate
        self.device = device
        self.count = 0
        self.expected = 100

    def generate(self, size):
        data = [128]*(self.width*self.height*3)
        self.count += 1
        print(f"Generating buffer {self.count}/{self.expected}")
        return Buffer() if self.count == self.expected else Buffer(data)

Flow(Pipeline("playback")).inject([MyBufferProvider(640, 480)]).render()()
