"""Capture one full task transition/reset on a shared Torch/Warp CUDA stream."""
import torch
import warp as wp


class CudaRunner:
    def __init__(self,task,capture=True):
        self.task=task
        self.actions=torch.zeros((task.n,12),device='cuda')
        self.graph=None
        if capture:
            stream=torch.cuda.Stream()
            warp_stream=wp.stream_from_torch(stream)
            stream.wait_stream(torch.cuda.current_stream())
            with torch.cuda.stream(stream),wp.ScopedStream(warp_stream):
                for _ in range(3):
                    task.step(self.actions)
                    task.reset(torch.ones(task.n,dtype=torch.bool,device='cuda'))
            torch.cuda.current_stream().wait_stream(stream)
            graph=torch.cuda.CUDAGraph()
            with torch.cuda.graph(graph,stream=stream),wp.ScopedStream(warp_stream),wp.ScopedCapture(stream=warp_stream,external=True) as capture_context:
                raw,reward,term,timeout,metrics=task.step(self.actions)
                reset=task.reset(term|timeout)
                self.output=(raw,reward,term,timeout,metrics,reset)
            self.warp_graph=capture_context.graph
            self.graph=graph
            # Capture executes a transition once; initialize a clean rollout state.
            task.reset(torch.ones(task.n,dtype=torch.bool,device='cuda'))

    def step(self,actions):
        if self.graph is not None:
            self.actions.copy_(actions)
            self.graph.replay()
            return self.output
        raw,reward,term,timeout,metrics=self.task.step(actions)
        return raw,reward,term,timeout,metrics,self.task.reset(term|timeout)
