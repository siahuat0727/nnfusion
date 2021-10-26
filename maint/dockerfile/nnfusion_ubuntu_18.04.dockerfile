# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

FROM nvidia/cuda:11.3.1-cudnn8-devel-ubuntu16.04
RUN apt update && apt install -y git
# FIXME
# RUN git clone https://github.com/microsoft/nnfusion.git /root/nnfusion --branch master --single-branch
RUN git clone https://github.com/siahuat0727/nnfusion.git /root/nnfusion --branch siahuat0727/update-dependency --single-branch
# - Install Requirements
RUN bash /root/nnfusion/maint/script/install_dependency.sh
# - Make Install
RUN cd /root/nnfusion/ && mkdir build && cd build && cmake .. && make -j6 && make install
# - Execute command
RUN LD_LIBRARY_PATH=/usr/local/lib nnfusion /root/nnfusion/test/models/tensorflow/frozen_op_graph/frozen_abs_graph.pb
# FIXME remove
RUN wget https://nnfusion.blob.core.windows.net/models/tensorflow/frozen_lstm_l8s8h256_bs1.pb
RUN LD_LIBRARY_PATH=/usr/local/lib nnfusion frozen_lstm_l8s8h256_bs1.pb
