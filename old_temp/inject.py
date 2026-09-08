from pyservicemaker import Pipeline, Flow, BufferProvider, Buffer

class MyBufferProvider(BufferProvider):

    def __init__(self, width, height, device='cpu', framerate=30, format="RGB"):
        super().__init__()
        self.width = width
        self.height = height
        self.format = format
        self.framerate = framerate
        self.device = device
        self.count = 0
        self.expected = 255

    def generate(self, size):
        data = [self.count]*(self.width*self.height*3)
        if self.count < self.expected:
            self.count += 1
        return Buffer() if self.count == self.expected else Buffer(data)

p = MyBufferProvider(320, 240)
# playback a mp4 video
Flow(Pipeline("playback")).inject([p]).render()()