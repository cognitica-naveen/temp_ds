from pyservicemaker import Pipeline, Flow, Probe, BatchMetadataOperator
import torch

class TensorOutput(BatchMetadataOperator):
    def handle_metadata(self, batch_meta):
        for frame_meta in batch_meta.frame_items:
            for user_meta in frame_meta.tensor_items:
                for n, tensor in user_meta.as_tensor_output().get_layers().items():
                    print(f"tensor name: {n}")
                    print(f"tensor object: {tensor}")
                    # operations on tensors:
                    torch_tensor = torch.utils.dlpack.from_dlpack(tensor.clone())

pipeline = Pipeline("detector")
infer_config = "/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_infer_primary.yml"
video_file = "/opt/nvidia/deepstream/deepstream/samples/streams/sample_1080p_h264.mp4"
probe = Probe('tensor_retriver', TensorOutput())
Flow(pipeline).batch_capture([video_file]).infer(infer_config, output_tensor_meta=True).attach(probe).render()()

