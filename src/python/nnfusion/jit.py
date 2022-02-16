import functools

import torch

from .jit_utils import TorchModule
from .runtime import NNFusionRT


def nrt_forward(obj, *inputs):
    if not isinstance(obj, torch.nn.Module):
        return nrt_forward(TorchModule(obj), *inputs)

    # TODO Pass other arguments from nrt_jit?
    # def nrt_forward(obj, *inputs, **kwargs):
    #     ...
    #     NNFusionRT(obj, inputs, outputs, **kwargs)
    nnf = NNFusionRT(obj, server="127.0.0.1:8880", steps=2000)

    def forward(*inputs):
        return nnf.run(inputs)

    return forward


def jit(func):
    @functools.wraps(func)
    def wrapper(*args):  # TODO support kwargs?
        if wrapper.forward is None:
            wrapper.forward = nrt_forward(func, *args)
        return wrapper.forward(*args)
    wrapper.forward = None
    return wrapper
