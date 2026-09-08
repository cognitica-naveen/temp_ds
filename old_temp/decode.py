from pyservicemaker import Pipeline, Flow, BufferRetriever, BufferProvider, Buffer

class JpegBufferProvider(BufferProvider):

    def __init__(self, file_path:str):
        super().__init__()
        self._file_path = file_path
        self.format = "JPEG"
        self.width = 1280
        self.height = 720
        self.framerate = 0
        self.count = 0
        self.expected = 255

    def generate(self, size):
        data = []
        with open(self._file_path, "rb") as f:
            bytes = f.read()
            data = [int(b) for b in bytes]
        if self.count < self.expected:
            self.count += 1
        return Buffer() if self.count == self.expected else Buffer(data)

# decode jpeg from a binary buffer
jpeg_file = "/opt/nvidia/deepstream/deepstream/samples/streams/sample_720p.jpg"
Flow(Pipeline("test")).inject([JpegBufferProvider(jpeg_file)]).decode().render()()