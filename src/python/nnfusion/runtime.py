import filecmp
import inspect
import os
import re
import tempfile
from pathlib import Path

import torch
import torch.onnx

from .data_format import cast_pytorch_tensor
from .executor import Executor
from .jit_utils import TorchModule
from .session import build, codegen, modify_nnfusion_rt


class TensorsDesc:
    """Save tensors description"""

    KEYS = ['shape', 'dtype', 'device']

    def __init__(self, tensors):
        assert isinstance(tensors, (tuple, list))
        self._descs = [self._tensor2desc(t) for t in tensors]

    @classmethod
    def _tensor2desc(cls, tensor):
        return {
            key: getattr(tensor, key)
            for key in cls.KEYS
        }

    @property
    def code(self):

        def get_dtype(desc):
            return {
                torch.float32: 'f32',
                torch.float64: 'f64',
            }.get(desc['dtype'], 'unknown-type')

        def encode(desc):
            shape = 'x'.join(str(shape) for shape in desc['shape'])
            dtype = get_dtype(desc)
            return '-'.join((shape, dtype))

        return '+'.join(encode(desc) for desc in self._descs)

    def empty_like_me(self):
        return [
            torch.empty(desc['shape'], dtype=desc['dtype'],
                        device=desc['device'])
            for desc in self._descs
        ]


class NNFusionRT:
    def __init__(self, model, server="127.0.0.1:8880", steps=1000,
                 force_build=False):
        self.model = model

        self.workdir = os.path.join("tmp", self._signature)
        if force_build:
            # TODO
            pass

        self.compile_flag = self._get_compile_flag(steps, server)
        self._infos = {}

    def _compile(self, inputs, outputs):
        output_is_tensor = isinstance(outputs, torch.Tensor)
        if output_is_tensor:
            outputs = [outputs]

        inputs_desc = TensorsDesc(inputs)

        workdir = os.path.join(self.workdir, inputs_desc.code)
        onnx_path = os.path.join(workdir, "model.onnx")
        rt_dir = os.path.join(workdir, "nnfusion_rt/cuda_codegen")

        if not os.path.isdir(workdir):
            os.makedirs(workdir)

        def export_onnx(fname):
            input_names = ["input" + str(i) for i in range(len(inputs))]
            output_names = ["output" + str(i) for i in range(len(outputs))]
            torch.onnx.export(self.model, inputs, fname,
                              input_names=input_names,
                              output_names=output_names)  # , opset_version=11)

        def check_if_need_build():
            if not os.path.exists(onnx_path):
                return True

            # Compare onnx file to check if modified
            with tempfile.TemporaryDirectory(dir=workdir) as tmp:
                temp_onnx_path = os.path.join(tmp, "temp.onnx")
                export_onnx(temp_onnx_path)

                if not filecmp.cmp(temp_onnx_path, onnx_path):
                    # Replace the original to avoid exporting onnx twice
                    os.remove(onnx_path)
                    os.link(temp_onnx_path, onnx_path)
                    return True

            if not os.path.exists(os.path.join(rt_dir, 'main_test')):
                return True

            return False

        def do_compile():
            if not os.path.exists(onnx_path):
                export_onnx(onnx_path)

            codegen(onnx_path, self.compile_flag, workdir)
            modify_nnfusion_rt(rt_dir)
            build(rt_dir)

        if check_if_need_build():
            do_compile()

        self._infos[inputs_desc.code] = {
            'workdir': workdir,
            'outputs_info': (TensorsDesc(outputs), output_is_tensor),
            'executor': Executor(rt_dir),
        }

    def _have_compiled_kernel(self, inputs_desc):
        return inputs_desc.code in self._infos

    def run(self, inputs):
        if not isinstance(inputs, (tuple, list)):
            inputs = [inputs]

        inputs_desc = TensorsDesc(inputs)

        if not self._have_compiled_kernel(inputs_desc):
            with torch.no_grad():
                # FIXME should we limit that model cannot receive list?
                outputs = self.model(*inputs)
            self._compile(inputs, outputs)

        outputs_desc, output_is_tensor = self._infos[inputs_desc.code]['outputs_info']
        executor = self._infos[inputs_desc.code]['executor']

        outputs = outputs_desc.empty_like_me()

        in_dict = {
            desc.name: cast_pytorch_tensor(tensor)
            for desc, tensor in zip(executor.get_inputs(), inputs)
        }
        out_dict = {
            desc.name: cast_pytorch_tensor(tensor)
            for desc, tensor in zip(executor.get_outputs(), outputs)
        }
        executor(in_dict, out_dict)

        if output_is_tensor:
            return outputs[0]
        return outputs

    @staticmethod
    def _get_compile_flag(tuning_step, codegen_server):
        return " ".join([
            "-f onnx",
            "-fextern_result_memory=1",
            "-fkernel_tuning_steps=" + str(tuning_step),
            "-fir_based_fusion=1",
            "-fkernel_fusion_level=0",
            # "-fantares_mode=1",
            # f"-fantares_codegen_server={codegen_server}",
            "-fblockfusion_level=0",
        ])

    @property
    def _signature(self):
        """
        Signature of a function or torch.nn.Module instance to detect reusable
        kernel.
        """
        def get_qualname():
            if isinstance(self.model, TorchModule):
                name = self.model.func.__qualname__
            else:
                name = self.model.__class__.__qualname__
            # Remove special chars to avoid the trouble of dealing with paths
            return re.sub("[<>]", "", name)

        def get_path():
            # Avoid collision between different files
            if isinstance(self.model, TorchModule):
                obj_path = inspect.getsourcefile(self.model.func)
            else:
                obj_path = inspect.getsourcefile(self.model.__class__)
            relpath = os.path.relpath(obj_path)
            return "-".join(Path(os.path.splitext(relpath)[0]).parts)

        return "-".join((get_path(), get_qualname()))
